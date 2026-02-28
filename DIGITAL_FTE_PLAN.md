
# DIGITAL FTE — COMPLETE CORRECTED DOCUMENT

---

## TABLE OF CONTENTS

1. EXECUTIVE SUMMARY
2. BUSINESS REQUIREMENTS
3. SYSTEM ARCHITECTURE
4. MULTI-AGENT DESIGN
5. TECHNICAL STACK
6. DATABASE DESIGN
7. API KEYS & INTEGRATIONS
8. WORKFLOWS (DETAILED)
9. UI/UX DESIGN
10. USER JOURNEY
11. OBSERVABILITY & MONITORING
12. PROJECT STRUCTURE
13. IMPLEMENTATION PHASES
14. ANTIGRAVITY EXECUTION INSTRUCTIONS

---

## 1. EXECUTIVE SUMMARY

Digital FTE is an AI-powered multi-agent system that acts as a full-time employee dedicated to a candidate's job search. It ingests a CV, finds matching jobs across major platforms, rewrites the CV to match each job posting at 100%, extracts HR contact information, sends tailored applications via email, and prepares the candidate for interviews — all orchestrated through an intelligent agent pipeline with full observability.

---

## 2. BUSINESS REQUIREMENTS

### 2.1 Functional Requirements

```
ID       | Requirement                                    | Priority
---------|------------------------------------------------|----------
FR-001   | User uploads CV (PDF/DOCX)                     | P0
FR-002   | AI parses and understands CV deeply             | P0
FR-003   | Search 10 jobs per request from LinkedIn,       | P0
         | Indeed, Glassdoor                               |
FR-004   | Fetch complete job description data             | P0
FR-005   | Customize CV per job (100% match rewrite)       | P0
FR-006   | Generate professional PDF CV output             | P0
FR-007   | Extract HR name and email from job posting      | P0
FR-008   | Send tailored CV to HR via Gmail API            | P0
FR-009   | Interview preparation module                    | P0
FR-010   | Chat interface for user interaction             | P0
FR-011   | Dashboard with analytics and status tracking    | P1
FR-012   | Connect to Google Drive, Docs, Gmail            | P1
FR-013   | PPTX slide generation for interview prep        | P1
FR-014   | Agent observability (what agent is doing,       | P0
         | plan, flow)                                     |
FR-015   | Multi-agent orchestration with LangGraph        | P0
FR-016   | Tracing and logging with LangSmith/LangFuse    | P0
FR-017   | Quota management for free-tier API keys         | P1
FR-018   | Job application status tracking                 | P1
FR-019   | Cover letter generation per job                 | P1
FR-020   | Skill gap analysis between CV and job           | P1
```

### 2.2 Non-Functional Requirements

```
NFR-001  | Response time < 30s for job search
NFR-002  | System handles 100 concurrent users
NFR-003  | 99.5% uptime
NFR-004  | All data encrypted at rest and in transit
NFR-005  | GDPR compliant data handling
NFR-006  | Modular architecture for easy expansion
NFR-007  | Rate limiting for free-tier API quota protection
NFR-008  | Graceful degradation when API limits hit
```

### 2.3 Business Rules

```
BR-001   | Maximum 10 jobs fetched per single request
BR-002   | Each job gets a uniquely customized CV
BR-003   | CV customization must preserve truthful information
         | (enhance presentation, not fabricate)
BR-004   | Email sending requires user approval before dispatch
BR-005   | Interview prep adapts to specific company + role
BR-006   | Free-tier quota tracked and user warned at 80% usage
BR-007   | All agent actions are logged and auditable
```

---

## 3. SYSTEM ARCHITECTURE

### 3.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                       FRONTEND (Next.js 15)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │  Dashboard    │  │  Chat UI     │  │  Observability Panel     │  │
│  │  - Job Cards  │  │  - Agent Chat│  │  - Agent Status          │  │
│  │  - Analytics  │  │  - File Upload│ │  - Flow Visualization    │  │
│  │  - Status     │  │  - Commands  │  │  - Logs & Traces         │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
└─────────────────────────────┬───────────────────────────────────────┘
                              │ REST API + WebSocket
┌─────────────────────────────┴───────────────────────────────────────┐
│                      API GATEWAY (FastAPI)                          │
│  ┌─────────┐ ┌──────────┐ ┌───────────┐ ┌────────┐ ┌───────────┐  │
│  │Auth     │ │Rate      │ │WebSocket  │ │File    │ │Quota      │  │
│  │Middleware│ │Limiter   │ │Manager    │ │Upload  │ │Manager    │  │
│  └─────────┘ └──────────┘ └───────────┘ └────────┘ └───────────┘  │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
┌─────────────────────────────┴───────────────────────────────────────┐
│                 ORCHESTRATION LAYER (LangGraph)                     │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                   SUPERVISOR AGENT                            │   │
│  │         (Routes tasks to specialized agents)                  │   │
│  └──────┬──────┬──────┬──────┬──────┬──────┬──────┬────────────┘   │
│         │      │      │      │      │      │      │                 │
│    ┌────┴┐ ┌──┴──┐ ┌─┴──┐ ┌┴───┐ ┌┴───┐ ┌┴───┐ ┌┴─────┐         │
│    │CV   │ │Job  │ │CV  │ │HR  │ │Email│ │Intv│ │Doc   │         │
│    │Parse│ │Hunt │ │Tailor│ │Find│ │Send│ │Prep│ │Gen   │         │
│    │Agent│ │Agent│ │Agent│ │Agent│ │Agent│ │Agent│ │Agent │         │
│    └─────┘ └─────┘ └────┘ └────┘ └────┘ └────┘ └──────┘         │
│                                                                     │
└───────────────┬──────────────────────┬──────────────────────────────┘
                │                      │
┌───────────────┴──────┐  ┌───────────┴──────────────────────────────┐
│   LLM ROUTER         │  │         TOOL LAYER                       │
│  ┌────────────────┐   │  │  ┌──────────┐ ┌──────────┐ ┌─────────┐ │
│  │Gemini 2.0 Flash│   │  │  │SerpAPI/  │ │Google    │ │WeasyPrint│ │
│  │(Primary)       │   │  │  │RapidAPI  │ │Cloud APIs│ │/ReportLab│ │
│  ├────────────────┤   │  │  │(Jobs)    │ │(Gmail,   │ │(PDF Gen) │ │
│  │Groq - Llama3.3 │   │  │  └──────────┘ │Drive,Doc)│ └─────────┘ │
│  │(Fallback)      │   │  │               └──────────┘              │
│  ├────────────────┤   │  │  ┌──────────┐ ┌──────────┐ ┌─────────┐ │
│  │Groq - Mixtral  │   │  │  │python-   │ │Hunter.io/│ │Playwright│ │
│  │(Fallback 2)    │   │  │  │pptx      │ │Apollo.io │ │(Scraping)│ │
│  └────────────────┘   │  │  │(Slides)  │ │(HR Email)│ │          │ │
│                        │  │  └──────────┘ └──────────┘ └─────────┘ │
└────────────────────────┘  └────────────────────────────────────────┘
                │                      │
┌───────────────┴──────────────────────┴──────────────────────────────┐
│                    OBSERVABILITY LAYER                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │  LangSmith    │  │  LangFuse    │  │  Custom Event Bus        │  │
│  │  (Tracing)    │  │  (Analytics) │  │  (Real-time WebSocket)   │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
┌─────────────────────────────┴───────────────────────────────────────┐
│                      DATA LAYER (ALL CLOUD)                         │
│  ┌──────────────────────────┐  ┌────────────────────────────────┐  │
│  │  Supabase                 │  │  Upstash Redis                 │  │
│  │  ├─ PostgreSQL (Primary   │  │  (Cache + Queue +              │  │
│  │  │   Database)            │  │   Rate Limiting)               │  │
│  │  ├─ pgvector (Vector      │  │  Free: 10K commands/day,      │  │
│  │  │   Store for CV + Job   │  │        256MB storage           │  │
│  │  │   Embeddings)          │  │                                │  │
│  │  ├─ Storage (File Store   │  └────────────────────────────────┘  │
│  │  │   for CVs, PDFs)       │                                      │
│  │  └─ Auth (optional)       │                                      │
│  │  Free: 500MB DB,          │                                      │
│  │        1GB Storage,        │                                      │
│  │        pgvector included   │                                      │
│  └──────────────────────────┘                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 Data Flow Architecture

```
User uploads CV
       │
       ▼
┌─────────────┐     ┌──────────────┐     ┌────────────────┐
│ CV Parser   │────▶│ CV Vector    │────▶│ Skill Extractor│
│ Agent       │     │ Store        │     │                │
└─────────────┘     │ (Supabase    │     └───────┬────────┘
                    │  pgvector)   │             │
                    └──────────────┘             │
       ┌────────────────────────────────────────┘
       ▼
┌─────────────┐     ┌──────────────┐     ┌────────────────┐
│ Job Hunter  │────▶│ Job Data     │────▶│ Match Scorer   │
│ Agent       │     │ Fetcher      │     │                │
└─────────────┘     └──────────────┘     └───────┬────────┘
                                                  │
       ┌──────────────────────────────────────────┘
       ▼
┌─────────────┐     ┌──────────────┐     ┌────────────────┐
│ CV Tailor   │────▶│ PDF Generator│────▶│ Quality Check  │
│ Agent       │     │              │     │ Agent          │
└─────────────┘     └──────────────┘     └───────┬────────┘
                                                  │
       ┌──────────────────────────────────────────┘
       ▼
┌─────────────┐     ┌──────────────┐     ┌────────────────┐
│ HR Finder   │────▶│ Email Composer│───▶│ Email Sender   │
│ Agent       │     │ Agent        │     │ Agent          │
└─────────────┘     └──────────────┘     └───────┬────────┘
                                                  │
       ┌──────────────────────────────────────────┘
       ▼
┌─────────────┐     ┌──────────────┐
│ Interview   │────▶│ Prep Material│
│ Prep Agent  │     │ Generator    │
└─────────────┘     └──────────────┘
```

---

## 4. MULTI-AGENT DESIGN

### 4.1 Agent Definitions

```yaml
agents:
  supervisor_agent:
    role: "Master Orchestrator"
    description: >
      Routes user requests to appropriate specialized agents.
      Manages workflow state. Decides which agent to invoke next.
      Handles error recovery and fallback logic.
    framework: LangGraph StateGraph
    llm: gemini-2.0-flash
    tools: [router, state_manager, error_handler]

  cv_parser_agent:
    role: "CV Intelligence Analyst"
    description: >
      Parses uploaded CV (PDF/DOCX). Extracts structured data:
      personal info, skills, experience, education, projects,
      certifications. Creates embeddings for semantic matching.
    framework: LangChain + LangGraph node
    llm: gemini-2.0-flash
    tools: [pdf_reader, docx_reader, embedding_generator]
    output_schema:
      personal_info:
        name: string
        email: string
        phone: string
        location: string
        linkedin: string
        github: string
        portfolio: string
      summary: string
      skills:
        technical: list[string]
        soft: list[string]
        tools: list[string]
      experience:
        - company: string
          role: string
          duration: string
          start_date: date
          end_date: date
          description: string
          achievements: list[string]
          technologies: list[string]
      education:
        - institution: string
          degree: string
          field: string
          year: string
          gpa: string
      projects:
        - name: string
          description: string
          technologies: list[string]
          link: string
      certifications: list[string]
      languages: list[string]

  job_hunter_agent:
    role: "Job Market Intelligence Scout"
    description: >
      Searches LinkedIn, Indeed, Glassdoor for relevant jobs.
      Returns 10 jobs per request with full details.
      Ranks by match score against parsed CV.
    framework: LangChain + LangGraph node
    llm: gemini-2.0-flash
    tools: [serpapi_search, rapidapi_jobs, web_scraper]
    output_schema:
      jobs:
        - id: string
          title: string
          company: string
          location: string
          salary_range: string
          job_type: string  # full-time, remote, hybrid
          description: string
          requirements: list[string]
          nice_to_have: list[string]
          responsibilities: list[string]
          posted_date: string
          application_url: string
          source: string  # linkedin, indeed, glassdoor
          match_score: float  # 0-100
          missing_skills: list[string]
          matching_skills: list[string]

  cv_tailor_agent:
    role: "CV Transformation Specialist"
    description: >
      Takes parsed CV data + specific job description.
      Rewrites entire CV to match 100% of job requirements.
      Optimizes keywords, restructures experience bullets,
      highlights relevant skills. Preserves truthfulness.
    framework: LangChain + LangGraph node
    llm: gemini-2.0-flash
    tools: [cv_rewriter, keyword_optimizer, ats_scorer]
    strategy: |
      1. Extract all keywords from job description
      2. Map candidate experience to job requirements
      3. Rewrite summary targeting the specific role
      4. Reorder and rewrite experience bullets with job keywords
      5. Highlight matching skills, reframe adjacent skills
      6. Add relevant projects
      7. Optimize for ATS (Applicant Tracking System)
      8. Score the tailored CV against job description

  hr_finder_agent:
    role: "HR Contact Intelligence Agent"
    description: >
      Finds the hiring manager or HR contact for each job.
      Extracts name and email using multiple strategies.
    framework: LangChain + LangGraph node
    llm: groq-llama3.3-70b
    tools: [hunter_io, apollo_io, linkedin_scraper, google_search]
    strategy: |
      1. Search company + "hiring manager" + role on Google
      2. Use Hunter.io to find email patterns
      3. Use Apollo.io for contact lookup
      4. Scrape LinkedIn for recruiter profiles
      5. Construct email if pattern found
      6. Verify email deliverability

  email_sender_agent:
    role: "Professional Communication Agent"
    description: >
      Composes personalized cover email for each application.
      Attaches the tailored CV PDF. Sends via Gmail API.
      Requires user approval before sending.
    framework: LangChain + LangGraph node
    llm: gemini-2.0-flash
    tools: [gmail_api, email_composer, pdf_attacher]

  interview_prep_agent:
    role: "Interview Coach"
    description: >
      Prepares candidate for specific role + company.
      Generates technical questions, behavioral questions,
      company research, salary negotiation tips.
      Can create PPTX study materials.
    framework: LangChain + LangGraph node
    llm: gemini-2.0-flash
    tools: [question_generator, company_researcher, pptx_generator]
    output:
      - company_overview: string
      - culture_insights: string
      - technical_questions: list[QA]
      - behavioral_questions: list[QA]
      - situational_questions: list[QA]
      - salary_research: object
      - tips: list[string]
      - study_slides: pptx_file

  document_generator_agent:
    role: "Document Production Specialist"
    description: >
      Generates professional PDFs (CVs, cover letters),
      PPTX presentations (interview prep), and other docs.
      Uploads to Supabase Storage and optionally Google Drive.
    framework: LangChain + LangGraph node
    llm: groq-llama3.3-70b
    tools: [weasyprint, reportlab, python_pptx, supabase_storage, google_drive_api]
```

### 4.2 LangGraph State Machine

```python
# Conceptual State Graph Definition

from langgraph.graph import StateGraph, START, END
from typing import TypedDict, List, Optional, Annotated

class DigitalFTEState(TypedDict):
    # User Input
    user_id: str
    raw_cv_path: str
    user_message: str
    
    # Parsed CV
    parsed_cv: dict
    cv_embeddings: list
    
    # Job Search
    search_query: str
    target_role: str
    target_location: str
    jobs_found: List[dict]
    selected_jobs: List[dict]
    
    # Tailored CVs
    tailored_cvs: List[dict]  # {job_id, tailored_cv_data, pdf_path, match_score}
    
    # HR Contacts
    hr_contacts: List[dict]  # {job_id, hr_name, hr_email, confidence}
    
    # Applications
    applications_sent: List[dict]  # {job_id, email_sent, timestamp, status}
    pending_approvals: List[dict]
    
    # Interview Prep
    interview_prep_data: List[dict]
    
    # Agent Tracking
    current_agent: str
    agent_plan: str
    agent_status: str
    execution_log: List[dict]
    errors: List[str]
    
    # Control Flow
    next_step: str
    requires_user_input: bool
    user_approval_needed: bool


# Graph Definition
workflow = StateGraph(DigitalFTEState)

# Add nodes (agents)
workflow.add_node("supervisor", supervisor_agent)
workflow.add_node("cv_parser", cv_parser_agent)
workflow.add_node("job_hunter", job_hunter_agent)
workflow.add_node("cv_tailor", cv_tailor_agent)
workflow.add_node("hr_finder", hr_finder_agent)
workflow.add_node("email_sender", email_sender_agent)
workflow.add_node("interview_prep", interview_prep_agent)
workflow.add_node("doc_generator", document_generator_agent)
workflow.add_node("human_approval", human_approval_node)

# Entry point
workflow.add_edge(START, "supervisor")

# Conditional edges from supervisor
workflow.add_conditional_edges(
    "supervisor",
    route_to_agent,  # routing function
    {
        "parse_cv": "cv_parser",
        "find_jobs": "job_hunter",
        "tailor_cv": "cv_tailor",
        "find_hr": "hr_finder",
        "send_email": "human_approval",
        "prep_interview": "interview_prep",
        "generate_doc": "doc_generator",
        "end": END
    }
)

# Agent → Supervisor (report back)
for agent in ["cv_parser", "job_hunter", "cv_tailor", 
               "hr_finder", "interview_prep", "doc_generator"]:
    workflow.add_edge(agent, "supervisor")

# Human approval → Email sender or back to supervisor
workflow.add_conditional_edges(
    "human_approval",
    check_approval,
    {
        "approved": "email_sender",
        "rejected": "supervisor"
    }
)
workflow.add_edge("email_sender", "supervisor")

app = workflow.compile()
```

### 4.3 Agent Communication Protocol

```
┌────────────────────────────────────────────────────────┐
│                  MESSAGE FORMAT                         │
├────────────────────────────────────────────────────────┤
│ {                                                      │
│   "from_agent": "job_hunter",                         │
│   "to_agent": "supervisor",                           │
│   "message_type": "task_complete|error|need_input",   │
│   "timestamp": "2024-01-15T10:30:00Z",               │
│   "payload": { ... },                                 │
│   "metadata": {                                        │
│     "tokens_used": 1500,                              │
│     "llm_model": "gemini-2.0-flash",                  │
│     "execution_time_ms": 3200,                        │
│     "trace_id": "uuid"                                │
│   }                                                    │
│ }                                                      │
└────────────────────────────────────────────────────────┘
```

---

## 5. TECHNICAL STACK

### 5.1 Languages & Frameworks

```yaml
backend:
  language: Python 3.13
  web_framework: FastAPI
  async: asyncio + uvicorn
  task_queue: ARQ + Upstash Redis (lightweight async task queue)

ai_orchestration:
  agent_framework: LangGraph (v0.2.60+)
  chain_framework: LangChain (v0.3.14+)
  tracing: LangSmith
  analytics: LangFuse
  embeddings: sentence-transformers (all-MiniLM-L6-v2) # free, local

frontend:
  framework: Next.js 15 (App Router)
  language: TypeScript
  ui_library: shadcn/ui + Tailwind CSS
  state_management: Zustand
  real_time: Socket.io
  charts: Recharts
  flow_visualization: ReactFlow (for agent workflow display)

database:
  primary: Supabase (managed PostgreSQL with pgvector)
  cache: Upstash Redis (free cloud Redis)
  vector_store: Supabase pgvector (via vecs Python client)
  file_storage: Supabase Storage + Google Drive API
  orm: SQLAlchemy 2.0 + Alembic (migrations)
  supabase_client: supabase-py (for Storage, Auth helpers)

devops:
  containerization: Docker + Docker Compose
  ci_cd: GitHub Actions
  env_management: python-dotenv
```

### 5.2 LLM Configuration (All Free Tier)

```yaml
llm_models:
  primary:
    name: "Google Gemini 2.0 Flash"
    provider: Google AI Studio
    api: google-generativeai
    model_id: "gemini-2.0-flash"
    free_tier:
      rpm: 15        # requests per minute
      rpd: 1500      # requests per day
      tpm: 1000000   # tokens per minute
    use_for:
      - CV parsing
      - CV tailoring
      - Email composition
      - Interview prep
      - Supervisor routing

  fallback_1:
    name: "Groq - Llama 3.3 70B"
    provider: Groq
    api: groq
    model_id: "llama-3.3-70b-versatile"
    free_tier:
      rpm: 30
      rpd: 14400
      tpm: 131072
    use_for:
      - Fallback for all tasks
      - HR contact research
      - Document generation

  fallback_2:
    name: "Groq - Mixtral 8x7B"
    provider: Groq
    api: groq
    model_id: "mixtral-8x7b-32768"
    free_tier:
      rpm: 30
      rpd: 14400
      tpm: 131072
    use_for:
      - Simple extraction tasks
      - Classification
      - When other models hit limits

  fallback_3:
    name: "Groq - Llama 3.1 8B"
    provider: Groq
    api: groq
    model_id: "llama-3.1-8b-instant"
    free_tier:
      rpm: 30
      rpd: 14400
      tpm: 131072
    use_for:
      - Lightweight tasks
      - Summarization
      - Quick classifications

  embeddings:
    name: "all-MiniLM-L6-v2"
    provider: Local (HuggingFace)
    cost: Free (runs locally)
    use_for:
      - CV embeddings
      - Job description embeddings
      - Semantic matching

quota_management:
  strategy: "round-robin with priority fallback"
  description: >
    Primary model (Gemini Flash) used first.
    When rate limit approached (80% threshold),
    automatically switch to Groq Llama 3.3.
    If that also limited, fall to Mixtral.
    Track usage per model per day in Upstash Redis.
  implementation:
    - Track token count per model per minute/day in Upstash Redis
    - Before each call, check remaining quota
    - If < 20% remaining, switch to fallback
    - Log all switches for observability
    - Reset counters daily at midnight UTC
```

### 5.3 Key Python Packages

```txt
# requirements.txt

# ============================================================
# Web Framework
# ============================================================
fastapi>=0.115.6
uvicorn[standard]>=0.34.0
python-multipart>=0.0.18
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4

# ============================================================
# AI/LLM
# ============================================================
langchain>=0.3.14
langchain-core>=0.3.28
langchain-community>=0.3.14
langchain-google-genai>=2.0.7
langchain-groq>=0.2.4
langgraph>=0.2.60
langsmith>=0.2.10
langfuse>=2.57.0

# ============================================================
# Embeddings (runs locally, free)
# ============================================================
sentence-transformers>=3.3.1

# ============================================================
# Supabase (replaces local PostgreSQL + ChromaDB + file storage)
# ============================================================
supabase>=2.13.0
vecs>=0.4.3
storage3>=0.8.0

# ============================================================
# Upstash Redis (replaces local Redis)
# ============================================================
upstash-redis>=1.1.0
redis>=5.2.1

# ============================================================
# Document Processing
# ============================================================
pypdf>=5.1.0
python-docx>=1.1.2
pdfplumber>=0.11.4

# ============================================================
# Document Generation
# ============================================================
weasyprint>=63.1
reportlab>=4.2.5
python-pptx>=1.0.2
jinja2>=3.1.5
markdown>=3.7.1

# ============================================================
# Job Search
# ============================================================
google-search-results>=2.4.2

# ============================================================
# Google Cloud
# ============================================================
google-auth>=2.37.0
google-auth-oauthlib>=1.2.1
google-api-python-client>=2.159.0
google-auth-httplib2>=0.2.0

# ============================================================
# HR Contact Finding / Web Scraping
# ============================================================
requests>=2.32.3
beautifulsoup4>=4.12.3
playwright>=1.49.1

# ============================================================
# Database ORM (connects to Supabase PostgreSQL)
# ============================================================
sqlalchemy>=2.0.36
alembic>=1.14.1
asyncpg>=0.30.0
psycopg2-binary>=2.9.10
pgvector>=0.3.6

# ============================================================
# Task Queue (lightweight async alternative to Celery)
# ============================================================
arq>=0.26.1

# ============================================================
# Utilities
# ============================================================
pydantic>=2.10.4
pydantic-settings>=2.7.1
python-dotenv>=1.0.1
httpx>=0.28.1
tenacity>=9.0.0
structlog>=24.4.0

# ============================================================
# WebSocket
# ============================================================
websockets>=14.1

# ============================================================
# Testing
# ============================================================
pytest>=8.3.4
pytest-asyncio>=0.25.0
```

---

## 6. DATABASE DESIGN

### 6.1 Supabase PostgreSQL Schema

```sql
-- Run in Supabase Dashboard → SQL Editor

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    google_oauth_token JSONB,
    google_refresh_token TEXT,
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Original CVs uploaded by user
CREATE TABLE user_cvs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    file_name VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,           -- Supabase Storage path
    file_type VARCHAR(10) NOT NULL,    -- pdf, docx
    parsed_data JSONB NOT NULL,        -- structured CV data
    raw_text TEXT,
    is_primary BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- CV embeddings (replaces ChromaDB collection)
CREATE TABLE cv_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    cv_id UUID REFERENCES user_cvs(id) ON DELETE CASCADE,
    section VARCHAR(50) NOT NULL,      -- summary, experience, skills, education
    content TEXT NOT NULL,
    embedding vector(384),             -- 384 dims for all-MiniLM-L6-v2
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX ON cv_embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Job searches performed
CREATE TABLE job_searches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    cv_id UUID REFERENCES user_cvs(id),
    search_query TEXT NOT NULL,
    target_role VARCHAR(255),
    target_location VARCHAR(255),
    filters JSONB DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'pending',
    -- pending, searching, completed, failed
    created_at TIMESTAMP DEFAULT NOW()
);

-- Individual jobs found
CREATE TABLE jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    search_id UUID REFERENCES job_searches(id) ON DELETE CASCADE,
    external_id VARCHAR(255),          -- ID from source platform
    title VARCHAR(255) NOT NULL,
    company VARCHAR(255) NOT NULL,
    location VARCHAR(255),
    salary_range VARCHAR(100),
    job_type VARCHAR(50),
    description TEXT NOT NULL,
    requirements JSONB,
    nice_to_have JSONB,
    responsibilities JSONB,
    posted_date DATE,
    application_url TEXT,
    source VARCHAR(50) NOT NULL,       -- linkedin, indeed, glassdoor
    match_score FLOAT,
    matching_skills JSONB,
    missing_skills JSONB,
    raw_data JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Job description embeddings (replaces ChromaDB collection)
CREATE TABLE job_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID REFERENCES jobs(id) ON DELETE CASCADE,
    search_id UUID,
    title VARCHAR(255),
    company VARCHAR(255),
    source VARCHAR(50),
    content TEXT NOT NULL,
    embedding vector(384),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX ON job_embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Similarity search function
CREATE OR REPLACE FUNCTION match_jobs(
    query_embedding vector(384),
    match_threshold float DEFAULT 0.5,
    match_count int DEFAULT 10
)
RETURNS TABLE (
    id UUID,
    job_id UUID,
    title VARCHAR,
    company VARCHAR,
    content TEXT,
    similarity float
)
LANGUAGE sql STABLE
AS $$
    SELECT
        job_embeddings.id,
        job_embeddings.job_id,
        job_embeddings.title,
        job_embeddings.company,
        job_embeddings.content,
        1 - (job_embeddings.embedding <=> query_embedding) AS similarity
    FROM job_embeddings
    WHERE 1 - (job_embeddings.embedding <=> query_embedding) > match_threshold
    ORDER BY job_embeddings.embedding <=> query_embedding
    LIMIT match_count;
$$;

-- CV similarity search function
CREATE OR REPLACE FUNCTION match_cv_sections(
    query_embedding vector(384),
    target_user_id UUID,
    match_count int DEFAULT 10
)
RETURNS TABLE (
    id UUID,
    cv_id UUID,
    section VARCHAR,
    content TEXT,
    similarity float
)
LANGUAGE sql STABLE
AS $$
    SELECT
        cv_embeddings.id,
        cv_embeddings.cv_id,
        cv_embeddings.section,
        cv_embeddings.content,
        1 - (cv_embeddings.embedding <=> query_embedding) AS similarity
    FROM cv_embeddings
    WHERE cv_embeddings.user_id = target_user_id
    ORDER BY cv_embeddings.embedding <=> query_embedding
    LIMIT match_count;
$$;

-- Tailored CVs generated per job
CREATE TABLE tailored_cvs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    original_cv_id UUID REFERENCES user_cvs(id),
    job_id UUID REFERENCES jobs(id) ON DELETE CASCADE,
    tailored_data JSONB NOT NULL,
    pdf_path TEXT,                     -- Supabase Storage path
    cover_letter TEXT,
    ats_score FLOAT,
    match_score FLOAT,
    changes_made JSONB,
    version INT DEFAULT 1,
    status VARCHAR(50) DEFAULT 'draft',
    -- draft, approved, sent
    created_at TIMESTAMP DEFAULT NOW()
);

-- HR contacts found
CREATE TABLE hr_contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID REFERENCES jobs(id) ON DELETE CASCADE,
    hr_name VARCHAR(255),
    hr_email VARCHAR(255),
    hr_title VARCHAR(255),
    hr_linkedin VARCHAR(255),
    confidence_score FLOAT,
    source VARCHAR(100),
    verified BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Job applications sent
CREATE TABLE applications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    job_id UUID REFERENCES jobs(id) ON DELETE CASCADE,
    tailored_cv_id UUID REFERENCES tailored_cvs(id),
    hr_contact_id UUID REFERENCES hr_contacts(id),
    email_subject TEXT,
    email_body TEXT,
    email_sent_at TIMESTAMP,
    gmail_message_id VARCHAR(255),
    status VARCHAR(50) DEFAULT 'pending_approval',
    -- pending_approval, approved, sent, delivered,
    -- opened, replied, rejected, interview_scheduled
    user_approved BOOLEAN DEFAULT false,
    user_approved_at TIMESTAMP,
    follow_up_count INT DEFAULT 0,
    last_follow_up_at TIMESTAMP,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Interview preparations
CREATE TABLE interview_preps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    job_id UUID REFERENCES jobs(id) ON DELETE CASCADE,
    application_id UUID REFERENCES applications(id),
    company_research JSONB,
    technical_questions JSONB,
    behavioral_questions JSONB,
    situational_questions JSONB,
    salary_research JSONB,
    tips JSONB,
    study_material_path TEXT,          -- Supabase Storage path
    prep_score FLOAT,
    status VARCHAR(50) DEFAULT 'generating',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Agent execution logs (for observability)
CREATE TABLE agent_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    session_id UUID NOT NULL,
    agent_name VARCHAR(100) NOT NULL,
    action VARCHAR(255) NOT NULL,
    plan TEXT,
    input_data JSONB,
    output_data JSONB,
    llm_model VARCHAR(100),
    tokens_input INT,
    tokens_output INT,
    execution_time_ms INT,
    status VARCHAR(50),
    error_message TEXT,
    trace_id VARCHAR(255),
    langfuse_trace_id VARCHAR(255),
    parent_execution_id UUID REFERENCES agent_executions(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- API quota tracking
CREATE TABLE api_quota_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider VARCHAR(100) NOT NULL,
    model VARCHAR(100),
    date DATE NOT NULL,
    requests_used INT DEFAULT 0,
    tokens_used INT DEFAULT 0,
    requests_limit INT,
    tokens_limit INT,
    last_updated TIMESTAMP DEFAULT NOW(),
    UNIQUE(provider, model, date)
);

-- Chat messages (for chat interface)
CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    session_id UUID NOT NULL,
    role VARCHAR(20) NOT NULL,
    agent_name VARCHAR(100),
    content TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Connected external services
CREATE TABLE user_integrations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    service_name VARCHAR(100) NOT NULL,
    access_token TEXT,
    refresh_token TEXT,
    token_expiry TIMESTAMP,
    scopes JSONB,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, service_name)
);

-- Indexes
CREATE INDEX idx_jobs_search_id ON jobs(search_id);
CREATE INDEX idx_jobs_match_score ON jobs(match_score DESC);
CREATE INDEX idx_applications_user_id ON applications(user_id);
CREATE INDEX idx_applications_status ON applications(status);
CREATE INDEX idx_agent_executions_session ON agent_executions(session_id);
CREATE INDEX idx_agent_executions_agent ON agent_executions(agent_name);
CREATE INDEX idx_chat_messages_session ON chat_messages(session_id);
CREATE INDEX idx_api_quota_date ON api_quota_usage(provider, date);
CREATE INDEX idx_cv_embeddings_user ON cv_embeddings(user_id);
CREATE INDEX idx_job_embeddings_job ON job_embeddings(job_id);

-- Supabase Storage buckets setup
INSERT INTO storage.buckets (id, name, public)
VALUES
    ('cvs', 'cvs', false),
    ('generated', 'generated', false),
    ('templates', 'templates', true)
ON CONFLICT (id) DO NOTHING;
```

### 6.2 Upstash Redis Schema

```yaml
# Same key structure as before, hosted on Upstash Redis cloud
# All standard Redis commands work with Upstash

upstash_redis_keys:
  # Session management
  "session:{user_id}:{session_id}":
    type: hash
    fields:
      state: "JSON serialized LangGraph state"
      current_agent: "agent_name"
      last_activity: "timestamp"
    ttl: 3600  # 1 hour

  # API quota tracking (real-time)
  "quota:{provider}:{model}:rpm":
    type: string (counter)
    ttl: 60  # reset every minute

  "quota:{provider}:{model}:rpd:{date}":
    type: string (counter)
    ttl: 86400  # reset daily

  "quota:{provider}:{model}:tpm":
    type: string (counter)
    ttl: 60

  # Agent status (real-time observability)
  "agent_status:{session_id}":
    type: hash
    fields:
      current_agent: "cv_tailor"
      status: "processing"
      plan: "Rewriting experience section for DevOps role..."
      progress: "60"
      started_at: "timestamp"
    ttl: 3600

  # Task queue
  "arq:*":
    type: various (managed by ARQ task queue)

  # WebSocket channel mapping
  "ws:{user_id}":
    type: string
    value: "connection_id"
    ttl: 3600

  # NOTE: Upstash free tier = 10K commands/day
  # Optimize by:
  # - Batching with pipelines
  # - Using longer TTLs
  # - Combining related data into hash operations
  # - Avoiding frequent polling (use WebSocket push)
```

### 6.3 Supabase pgvector Schema

```yaml
# Replaces ChromaDB collections — now stored as PostgreSQL tables

vector_tables:
  cv_embeddings:
    description: "Embedded CV sections for semantic matching"
    table: cv_embeddings
    dimension: 384  # all-MiniLM-L6-v2
    distance_metric: cosine
    index_type: ivfflat
    columns:
      user_id: UUID (foreign key → users)
      cv_id: UUID (foreign key → user_cvs)
      section: string  # summary, experience, skills, education
      content: text
      embedding: vector(384)
      metadata: jsonb

  job_embeddings:
    description: "Embedded job descriptions for matching"
    table: job_embeddings
    dimension: 384
    distance_metric: cosine
    index_type: ivfflat
    columns:
      job_id: UUID (foreign key → jobs)
      search_id: UUID
      title: string
      company: string
      source: string
      content: text
      embedding: vector(384)
      metadata: jsonb

  search_functions:
    match_jobs: "Find similar jobs by embedding vector"
    match_cv_sections: "Find similar CV sections for a user"
```

---

## 7. API KEYS & INTEGRATIONS

### 7.1 Required API Keys

```yaml
api_keys_needed:

  # LLM APIs (FREE)
  google_ai_studio:
    key_name: GOOGLE_AI_API_KEY
    get_from: "https://aistudio.google.com/apikey"
    cost: Free
    used_for: Gemini 2.0 Flash
    limits: "15 RPM, 1500 RPD, 1M TPM"

  groq:
    key_name: GROQ_API_KEY
    get_from: "https://console.groq.com/keys"
    cost: Free
    used_for: Llama 3.3, Mixtral (fallback LLMs)
    limits: "30 RPM, 14400 RPD"

  # Cloud Database (FREE)
  supabase:
    key_name: SUPABASE_URL + SUPABASE_ANON_KEY + SUPABASE_SERVICE_ROLE_KEY
    get_from: "https://supabase.com"
    cost: Free tier (500MB DB, 1GB Storage, pgvector included)
    used_for: "Primary database, vector store, file storage"
    setup_steps:
      1: "Sign up at supabase.com"
      2: "Create new project"
      3: "Get URL and keys from Settings → API"
      4: "Get database connection string from Settings → Database"
      5: "Run setup SQL to enable pgvector extension"
      6: "Create storage buckets (cvs, generated, templates)"

  # Cloud Cache (FREE)
  upstash_redis:
    key_name: UPSTASH_REDIS_URL + UPSTASH_REDIS_REST_URL + UPSTASH_REDIS_REST_TOKEN
    get_from: "https://upstash.com"
    cost: Free tier (10K commands/day, 256MB)
    used_for: "Caching, rate limiting, session state, task queue"
    setup_steps:
      1: "Sign up at upstash.com"
      2: "Create new Redis database"
      3: "Choose region closest to your server"
      4: "Get Redis URL (rediss://...) and REST credentials"

  # Job Search APIs
  serpapi:
    key_name: SERPAPI_API_KEY
    get_from: "https://serpapi.com/manage-api-key"
    cost: Free tier (100 searches/month)
    used_for: Google Jobs search, LinkedIn jobs via Google
    alternative: "Use web scraping as fallback"

  rapidapi_jsearch:
    key_name: RAPIDAPI_KEY
    get_from: "https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch"
    cost: Free tier (500 requests/month)
    used_for: "Job search across LinkedIn, Indeed, Glassdoor"
    note: "JSearch API aggregates multiple job boards"

  # HR Contact Finding
  hunter_io:
    key_name: HUNTER_API_KEY
    get_from: "https://hunter.io/api-keys"
    cost: Free tier (25 searches/month)
    used_for: Finding HR email addresses
    alternative: "Apollo.io free tier"

  # Google Cloud (Gmail, Drive, Docs)
  google_cloud:
    key_name: GOOGLE_CLOUD_CREDENTIALS
    get_from: "https://console.cloud.google.com/"
    cost: Free (within personal use limits)
    setup_steps:
      1: "Create a Google Cloud Project"
      2: "Enable Gmail API, Google Drive API, Google Docs API"
      3: "Create OAuth 2.0 credentials (Desktop app type)"
      4: "Download credentials.json"
      5: "Configure OAuth consent screen"
    scopes_needed:
      - "https://www.googleapis.com/auth/gmail.send"
      - "https://www.googleapis.com/auth/gmail.readonly"
      - "https://www.googleapis.com/auth/drive.file"
      - "https://www.googleapis.com/auth/documents"

  # Observability (FREE)
  langsmith:
    key_name: LANGCHAIN_API_KEY
    get_from: "https://smith.langchain.com/"
    cost: Free tier (5000 traces/month)
    used_for: LLM call tracing, debugging

  langfuse:
    key_name: LANGFUSE_PUBLIC_KEY + LANGFUSE_SECRET_KEY
    get_from: "https://langfuse.com/"
    cost: Free tier (50k observations/month) OR self-host free
    used_for: Analytics, cost tracking, prompt management
    self_host: "Can run via Docker for unlimited free usage"

  # Optional but Recommended
  apollo_io:
    key_name: APOLLO_API_KEY
    get_from: "https://www.apollo.io/"
    cost: Free tier (limited searches)
    used_for: "Backup HR contact finding"
```

### 7.2 Environment Configuration

```env
# .env file

# ========== LLM PROVIDERS ==========
GOOGLE_AI_API_KEY=your_gemini_api_key
GROQ_API_KEY=your_groq_api_key

# ========== JOB SEARCH ==========
SERPAPI_API_KEY=your_serpapi_key
RAPIDAPI_KEY=your_rapidapi_key

# ========== HR CONTACT ==========
HUNTER_API_KEY=your_hunter_key

# ========== GOOGLE CLOUD ==========
GOOGLE_CLOUD_PROJECT_ID=your_project_id
GOOGLE_OAUTH_CLIENT_ID=your_client_id
GOOGLE_OAUTH_CLIENT_SECRET=your_client_secret
GOOGLE_CREDENTIALS_PATH=./credentials.json

# ========== SUPABASE ==========
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# SQLAlchemy connection via Supabase connection pooler (for app)
DATABASE_URL=postgresql+asyncpg://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres

# Direct connection (for Alembic migrations)
DIRECT_DATABASE_URL=postgresql://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres

# ========== UPSTASH REDIS ==========
UPSTASH_REDIS_URL=rediss://default:<password>@<endpoint>.upstash.io:6379
UPSTASH_REDIS_REST_URL=https://<endpoint>.upstash.io
UPSTASH_REDIS_REST_TOKEN=AXxxxxxxxxxxxxxxxxxxxx

# ========== OBSERVABILITY ==========
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_key
LANGCHAIN_PROJECT=digital-fte

LANGFUSE_PUBLIC_KEY=your_langfuse_public_key
LANGFUSE_SECRET_KEY=your_langfuse_secret_key
LANGFUSE_HOST=https://cloud.langfuse.com

# ========== APP CONFIG ==========
SECRET_KEY=your_jwt_secret_key_min_32_chars
APP_ENV=development
DEBUG=true
LOG_LEVEL=DEBUG
UPLOAD_DIR=./uploads
GENERATED_DIR=./generated
```

---

## 8. WORKFLOWS (DETAILED)

### 8.1 Master Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                    DIGITAL FTE MASTER WORKFLOW                    │
└─────────────────────────────────────────────────────────────────┘

PHASE 1: ONBOARDING
═══════════════════
User Signs Up → Connects Google Account → Uploads CV
       │                    │                    │
       ▼                    ▼                    ▼
  Create Profile    Store OAuth Tokens    CV Parser Agent
                                              │
                                              ▼
                                    ┌──────────────────┐
                                    │ Parsed CV stored  │
                                    │ in Supabase DB +  │
                                    │ pgvector           │
                                    └────────┬─────────┘
                                             │
PHASE 2: JOB HUNTING                         │
═════════════════════                        ▼
User says "Find me 10 DevOps jobs in NYC"
       │
       ▼
  Supervisor Agent analyzes request
       │
       ▼
  Job Hunter Agent
       │
       ├──▶ SerpAPI: Google Jobs search
       ├──▶ RapidAPI JSearch: LinkedIn + Indeed + Glassdoor
       │
       ▼
  Fetch full job descriptions (10 jobs)
       │
       ▼
  Match Scorer: Compare each job against CV
       │
       ▼
  Return 10 jobs ranked by match score
       │
       ▼
  Display in Dashboard with match analysis

PHASE 3: CV TAILORING
══════════════════════
For each of the 10 jobs (or user-selected ones):
       │
       ▼
  CV Tailor Agent receives:
    - Original parsed CV
    - Target job description
    - Job requirements
       │
       ▼
  ┌──────────────────────────────────────────┐
  │ TAILORING PROCESS:                        │
  │ 1. Extract ALL keywords from job desc     │
  │ 2. Map existing experience to requirements│
  │ 3. Rewrite professional summary           │
  │ 4. Rewrite each experience bullet point   │
  │    with relevant keywords                 │
  │ 5. Reorder skills to match priority       │
  │ 6. Add/highlight relevant projects        │
  │ 7. Generate tailored cover letter         │
  │ 8. ATS optimization pass                  │
  │ 9. Score tailored CV against job (0-100)  │
  └──────────────────────────┬───────────────┘
                             │
                             ▼
  Document Generator Agent → Create PDF
                             │
                             ▼
  Store: tailored CV data + PDF in Supabase DB + Storage

PHASE 4: HR CONTACT FINDING
════════════════════════════
For each job to apply:
       │
       ▼
  HR Finder Agent
       │
       ├──▶ Hunter.io: Email finder by domain
       ├──▶ Apollo.io: Contact database lookup
       ├──▶ Google Search: "{company} {role} hiring manager"
       ├──▶ LinkedIn scrape: Company page → People
       │
       ▼
  ┌────────────────────────────────────────┐
  │ STRATEGIES:                             │
  │ 1. Find company domain                 │
  │ 2. Hunter.io domain search             │
  │ 3. Search for HR/Recruiter by title    │
  │ 4. Construct email from pattern        │
  │    (first.last@company.com)            │
  │ 5. Verify email if possible            │
  │ 6. Assign confidence score             │
  └──────────────────────┬─────────────────┘
                         │
                         ▼
  Store: HR name, email, confidence in Supabase DB

PHASE 5: APPLICATION SENDING
═════════════════════════════
For each job application:
       │
       ▼
  Email Sender Agent composes email:
    - Personalized subject line
    - Professional cover email body
    - Attached: tailored CV PDF (from Supabase Storage)
       │
       ▼
  ┌─────────────────────────────────┐
  │ ⚠️ HUMAN APPROVAL GATE         │
  │                                 │
  │ Show user:                      │
  │ - Email preview                 │
  │ - Attached CV preview           │
  │ - HR contact details            │
  │ - Confidence score              │
  │                                 │
  │ [✅ Approve & Send] [✏️ Edit] [❌ Skip] │
  └───────────────┬─────────────────┘
                  │
                  ▼ (if approved)
  Send via Gmail API
                  │
                  ▼
  Update application status → "sent"
  Track for follow-ups

PHASE 6: INTERVIEW PREPARATION
═══════════════════════════════
When user reports interview scheduled:
       │
       ▼
  Interview Prep Agent
       │
       ├──▶ Company Research
       │     - Company overview, mission, values
       │     - Recent news, funding, products
       │     - Glassdoor reviews, culture
       │     - Tech stack (if tech role)
       │
       ├──▶ Question Generation
       │     - 15 technical questions with answers
       │     - 10 behavioral (STAR format)
       │     - 5 situational
       │     - Questions to ask interviewer
       │
       ├──▶ Salary Research
       │     - Market rate for role + location
       │     - Negotiation tips
       │
       ├──▶ Study Materials
       │     - PPTX presentation summary
       │     - PDF cheat sheet
       │
       └──▶ Mock Interview (Chat-based)
             - AI asks questions
             - User responds
             - AI gives feedback
       │
       ▼
  All materials stored in Supabase Storage and accessible in dashboard
```

### 8.2 LangGraph Workflow (Detailed)

```python
"""
DETAILED LANGGRAPH WORKFLOW DEFINITION
This is the conceptual implementation plan for Antigravity
"""

# ═══════════════════════════════════════════════
# WORKFLOW: FULL JOB APPLICATION PIPELINE
# ═══════════════════════════════════════════════

"""
State transitions:

START → supervisor
supervisor → cv_parser (if no CV parsed)
cv_parser → supervisor
supervisor → job_hunter (if user wants jobs)
job_hunter → supervisor
supervisor → cv_tailor (for each job)
cv_tailor → doc_generator (generate PDF)
doc_generator → supervisor
supervisor → hr_finder (find contacts)
hr_finder → supervisor
supervisor → email_composer (draft emails)
email_composer → human_approval
human_approval → email_sender (if approved)
human_approval → supervisor (if rejected/edited)
email_sender → supervisor
supervisor → interview_prep (if interview scheduled)
interview_prep → doc_generator (create materials)
doc_generator → supervisor
supervisor → END (when all tasks complete)
"""

# Routing logic pseudocode:
def supervisor_router(state):
    if not state.parsed_cv:
        return "cv_parser"
    
    if state.user_message contains job_search_intent:
        return "job_hunter"
    
    if state.jobs_found and not state.tailored_cvs:
        return "cv_tailor"
    
    if state.tailored_cvs and not state.hr_contacts:
        return "hr_finder"
    
    if state.hr_contacts and state.user_approval_needed:
        return "human_approval"
    
    if state.applications_approved:
        return "email_sender"
    
    if state.interview_scheduled:
        return "interview_prep"
    
    if state.needs_document:
        return "doc_generator"
    
    return "end"
```

### 8.3 Job Search Sub-Workflow

```
┌──────────────────────────────────────────────────────────┐
│              JOB SEARCH SUB-WORKFLOW                      │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Input: {role, location, experience_level, skills}       │
│                                                          │
│  1. CONSTRUCT SEARCH QUERIES                             │
│     ├─ Primary: "{role} {location}"                      │
│     ├─ LinkedIn: "site:linkedin.com/jobs {role}"         │
│     ├─ Indeed: "site:indeed.com {role} {location}"       │
│     └─ Glassdoor: "site:glassdoor.com {role}"            │
│                                                          │
│  2. PARALLEL API CALLS                                   │
│     ├─ SerpAPI → Google Jobs (returns aggregated)        │
│     ├─ RapidAPI JSearch → Multi-platform                 │
│     └─ Playwright scraping (fallback)                    │
│                                                          │
│  3. DEDUPLICATE RESULTS                                  │
│     └─ Match by (title + company + location) hash        │
│                                                          │
│  4. ENRICH EACH JOB                                      │
│     ├─ Fetch full description if truncated               │
│     ├─ Extract structured requirements                   │
│     └─ Identify tech stack / skills needed               │
│                                                          │
│  5. SCORE AGAINST CV                                     │
│     ├─ Semantic similarity (pgvector embeddings)         │
│     ├─ Keyword overlap percentage                        │
│     ├─ Experience level match                            │
│     └─ Composite score 0-100                             │
│                                                          │
│  6. RANK AND RETURN TOP 10                               │
│     └─ Sorted by match_score descending                  │
│                                                          │
│  Output: List[Job] with full data + match analysis       │
└──────────────────────────────────────────────────────────┘
```

### 8.4 CV Tailoring Sub-Workflow

```
┌──────────────────────────────────────────────────────────┐
│             CV TAILORING SUB-WORKFLOW                     │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Input: {parsed_cv, job_description, requirements}       │
│                                                          │
│  STEP 1: DEEP JOB ANALYSIS                               │
│  ├─ Extract: required_skills[]                           │
│  ├─ Extract: preferred_skills[]                          │
│  ├─ Extract: key_responsibilities[]                      │
│  ├─ Extract: key_action_verbs[]                          │
│  ├─ Extract: industry_keywords[]                         │
│  └─ Extract: ats_keywords[]                              │
│                                                          │
│  STEP 2: SKILL GAP ANALYSIS                              │
│  ├─ matching_skills = cv_skills ∩ job_skills            │
│  ├─ missing_skills = job_skills - cv_skills             │
│  ├─ transferable_skills = fuzzy_match(cv, job)          │
│  └─ hidden_skills = skills implied by experience         │
│                                                          │
│  STEP 3: PROFESSIONAL SUMMARY REWRITE                    │
│  ├─ Target the specific role title                       │
│  ├─ Include top 3-4 matching keywords                    │
│  ├─ Mention years of experience                          │
│  └─ Highlight biggest relevant achievement               │
│                                                          │
│  STEP 4: EXPERIENCE SECTION REWRITE                      │
│  ├─ For each position:                                   │
│  │   ├─ Rewrite bullets using job's action verbs         │
│  │   ├─ Quantify achievements (add metrics)              │
│  │   ├─ Embed relevant keywords naturally                │
│  │   └─ Highlight transferable accomplishments           │
│  └─ Reorder positions by relevance to target role        │
│                                                          │
│  STEP 5: SKILLS SECTION OPTIMIZATION                     │
│  ├─ Put matching skills first                            │
│  ├─ Group by category matching job description           │
│  ├─ Add transferable skills with relevant framing        │
│  └─ Remove irrelevant skills                             │
│                                                          │
│  STEP 6: PROJECTS & CERTIFICATIONS                       │
│  ├─ Highlight projects relevant to job                   │
│  ├─ Rewrite project descriptions with keywords           │
│  └─ Prioritize relevant certifications                   │
│                                                          │
│  STEP 7: COVER LETTER GENERATION                         │
│  ├─ Personalized opening (company + role)                │
│  ├─ 2-3 paragraphs mapping experience to needs           │
│  ├─ Enthusiasm for company mission/product               │
│  └─ Professional closing                                 │
│                                                          │
│  STEP 8: ATS OPTIMIZATION PASS                           │
│  ├─ Ensure all required keywords present                 │
│  ├─ Use standard section headings                        │
│  ├─ Remove graphics/tables (ATS unfriendly)              │
│  ├─ Proper date formatting                               │
│  └─ Clean formatting                                     │
│                                                          │
│  STEP 9: QUALITY SCORE                                   │
│  ├─ Keyword match: X%                                    │
│  ├─ ATS compatibility: X%                                │
│  ├─ Relevance score: X%                                  │
│  └─ Overall match: X%                                    │
│                                                          │
│  Output: {tailored_cv_data, cover_letter, scores,        │
│           changes_log}                                   │
└──────────────────────────────────────────────────────────┘
```

---

## 9. UI/UX DESIGN

### 9.1 Design System

```yaml
design_system:
  theme: "Professional Dark + Light mode"
  primary_color: "#6366F1"  # Indigo
  secondary_color: "#8B5CF6"  # Violet
  success_color: "#22C55E"
  warning_color: "#F59E0B"
  error_color: "#EF4444"
  
  typography:
    font_primary: "Inter"
    font_mono: "JetBrains Mono"
  
  components: "shadcn/ui"
  icons: "Lucide React"
  
  layout:
    sidebar: "Collapsible left sidebar"
    main: "Content area with tabs"
    right_panel: "Agent observability panel (toggleable)"
```

### 9.2 Page Structure

```
┌──────────────────────────────────────────────────────────────────┐
│  DIGITAL FTE - AI Job Application Assistant                      │
├──────┬───────────────────────────────────────────┬───────────────┤
│      │                                           │               │
│  S   │              MAIN CONTENT                 │  OBSERVABILITY│
│  I   │                                           │  PANEL        │
│  D   │  ┌─────────────────────────────────────┐  │               │
│  E   │  │                                     │  │  🤖 Agent:    │
│  B   │  │   [Dashboard] [Chat] [Jobs]         │  │  CV Tailor   │
│  A   │  │   [CVs] [Applications] [Interview]  │  │               │
│  R   │  │                                     │  │  📋 Plan:     │
│      │  │         PAGE CONTENT                 │  │  Rewriting   │
│  📊  │  │                                     │  │  experience  │
│  Dash│  │                                     │  │  section...  │
│      │  │                                     │  │               │
│  💬  │  │                                     │  │  ⏱️ Time:     │
│  Chat│  │                                     │  │  2.3s        │
│      │  │                                     │  │               │
│  💼  │  │                                     │  │  📊 Tokens:   │
│  Jobs│  │                                     │  │  1,234       │
│      │  │                                     │  │               │
│  📄  │  │                                     │  │  ──────────  │
│  CVs │  │                                     │  │  Flow:       │
│      │  │                                     │  │  [Visual     │
│  📨  │  │                                     │  │   Graph]     │
│  Apps│  │                                     │  │               │
│      │  │                                     │  │               │
│  🎯  │  │                                     │  │               │
│  Prep│  │                                     │  │               │
│      │  │                                     │  │               │
│  ⚙️  │  └─────────────────────────────────────┘  │               │
│  Set │                                           │               │
│      │                                           │               │
├──────┴───────────────────────────────────────────┴───────────────┤
│  Status Bar: 🟢 Connected | Gemini: 1234/1500 RPD | Groq: OK    │
└──────────────────────────────────────────────────────────────────┘
```

### 9.3 Page Designs

**Dashboard Page**
```
┌─────────────────────────────────────────────────────────┐
│  DASHBOARD                                               │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐│
│  │ 📄 CVs   │  │ 💼 Jobs  │  │ 📨 Apps  │  │ 🎯 Intv ││
│  │    3      │  │   27     │  │   15     │  │    2    ││
│  │ Uploaded  │  │  Found   │  │  Sent    │  │ Prepped ││
│  └──────────┘  └──────────┘  └──────────┘  └─────────┘│
│                                                         │
│  ┌─────────────────────────────────────────────────────┐│
│  │  RECENT ACTIVITY                                     ││
│  │  ─────────────────                                   ││
│  │  🟢 CV tailored for "Senior DevOps" at Google   2m  ││
│  │  🟡 Searching jobs for "ML Engineer"...         now  ││
│  │  🔵 Application sent to Amazon (HR: John Doe)   1h  ││
│  │  🟢 Interview prep ready for Microsoft          3h  ││
│  └─────────────────────────────────────────────────────┘│
│                                                         │
│  ┌──────────────────────┐  ┌──────────────────────────┐│
│  │  APPLICATION PIPELINE │  │  MATCH SCORE DISTRIBUTION ││
│  │                       │  │                          ││
│  │  Pending    ████ 5    │  │  90-100% ███ 3           ││
│  │  Sent       ██████ 8  │  │  70-89%  █████ 7         ││
│  │  Opened     ██ 2      │  │  50-69%  ████████ 12     ││
│  │  Interview  █ 1       │  │  <50%    █████ 5          ││
│  └──────────────────────┘  └──────────────────────────┘│
│                                                         │
│  ┌─────────────────────────────────────────────────────┐│
│  │  QUICK ACTIONS                                       ││
│  │  [🔍 Find Jobs] [📄 Upload CV] [💬 Chat with AI]    ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

**Chat Interface Page**
```
┌─────────────────────────────────────────────────────────┐
│  CHAT WITH DIGITAL FTE                                   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────────────────────────────────────────┐│
│  │                                                     ││
│  │  🤖 Digital FTE                                     ││
│  │  Hello! I'm your AI job assistant. I've analyzed    ││
│  │  your CV. You're a strong candidate for DevOps      ││
│  │  and Cloud Engineering roles. What would you like   ││
│  │  me to do?                                          ││
│  │                                                     ││
│  │  👤 You                                              ││
│  │  Find me 10 DevOps jobs in New York City,           ││
│  │  remote okay too.                                   ││
│  │                                                     ││
│  │  🤖 Digital FTE                                     ││
│  │  🔍 Searching across LinkedIn, Indeed, Glassdoor... ││
│  │                                                     ││
│  │  ┌─ Agent: Job Hunter ──────────────────────────┐  ││
│  │  │ ✅ SerpAPI: Found 6 jobs                      │  ││
│  │  │ ✅ JSearch API: Found 8 jobs                  │  ││
│  │  │ ✅ Deduplicated: 10 unique jobs               │  ││
│  │  │ ✅ Scored against your CV                     │  ││
│  │  └──────────────────────────────────────────────┘  ││
│  │                                                     ││
│  │  Found 10 jobs! Here are the top matches:           ││
│  │                                                     ││
│  │  ┌─ 1. Senior DevOps Engineer @ Google ──────────┐ ││
│  │  │  📍 NYC (Hybrid) | 💰 $180-220K                │ ││
│  │  │  🎯 Match: 92%                                 │ ││
│  │  │  ✅ Matching: K8s, Terraform, AWS, CI/CD       │ ││
│  │  │  ⚠️ Missing: GCP expertise                     │ ││
│  │  │  [Tailor CV] [View Details] [Skip]             │ ││
│  │  └────────────────────────────────────────────────┘ ││
│  │                                                     ││
│  │  ┌─ 2. Cloud DevOps Lead @ Netflix ──────────────┐ ││
│  │  │  📍 Remote | 💰 $200-250K                      │ ││
│  │  │  🎯 Match: 87%                                 │ ││
│  │  │  [Tailor CV] [View Details] [Skip]             │ ││
│  │  └────────────────────────────────────────────────┘ ││
│  │  ... (8 more jobs)                                  ││
│  │                                                     ││
│  └─────────────────────────────────────────────────────┘│
│                                                         │
│  ┌─────────────────────────────────────────────────────┐│
│  │ 📎 Attach  │  Type a message...           │  Send ▶ ││
│  └─────────────────────────────────────────────────────┘│
│                                                         │
│  Quick actions: [Find Jobs] [Tailor All CVs]            │
│  [Apply to Top 5] [Prepare for Interview]               │
└─────────────────────────────────────────────────────────┘
```

**Jobs Page**
```
┌─────────────────────────────────────────────────────────┐
│  JOBS FOUND                                  [🔍 Search]│
├─────────────────────────────────────────────────────────┤
│  Filters: [Role ▼] [Location ▼] [Source ▼] [Match ▼]  │
│                                                         │
│  ┌─────────────────────────────────────────────────────┐│
│  │  ☐ │ Senior DevOps Engineer                         ││
│  │    │ Google • NYC (Hybrid) • $180-220K              ││
│  │    │ Posted: 2 days ago • Source: LinkedIn           ││
│  │    │ Match: [████████░░] 92%                        ││
│  │    │                                                 ││
│  │    │ Skills: ✅K8s ✅Terraform ✅AWS ⚠️GCP           ││
│  │    │                                                 ││
│  │    │ Status: [CV Tailored ✅] [HR Found ✅]          ││
│  │    │         [Applied ⏳ Pending Approval]           ││
│  │    │                                                 ││
│  │    │ [📄 View Tailored CV] [📧 View Email Draft]    ││
│  │    │ [✅ Approve & Send] [🎯 Prep Interview]        ││
│  ├────┼─────────────────────────────────────────────────┤│
│  │  ☐ │ Cloud DevOps Lead                              ││
│  │    │ Netflix • Remote • $200-250K                   ││
│  │    │ ...                                             ││
│  └────┴─────────────────────────────────────────────────┘│
│                                                         │
│  [☑ Select All] [Tailor Selected CVs] [Apply Selected] │
└─────────────────────────────────────────────────────────┘
```

**Observability Panel (Right Side)**
```
┌───────────────────────────────┐
│  🔍 AGENT OBSERVATORY         │
├───────────────────────────────┤
│                               │
│  Current Session: #a1b2c3     │
│  ──────────────────────       │
│                               │
│  🤖 Active Agent:             │
│  ┌───────────────────────┐    │
│  │ CV TAILOR AGENT        │    │
│  │ Status: 🟡 Processing  │    │
│  │ Time: 4.2s elapsed     │    │
│  └───────────────────────┘    │
│                               │
│  📋 Current Plan:             │
│  ┌───────────────────────┐    │
│  │ 1. ✅ Extract keywords │    │
│  │ 2. ✅ Map experience   │    │
│  │ 3. 🔄 Rewrite summary │    │
│  │ 4. ⏳ Rewrite bullets  │    │
│  │ 5. ⏳ Optimize skills  │    │
│  │ 6. ⏳ Generate PDF     │    │
│  │ 7. ⏳ Score result     │    │
│  └───────────────────────┘    │
│                               │
│  📊 Token Usage:              │
│  Gemini: 1,234 / 1M TPM      │
│  [████░░░░░░] 12%             │
│                               │
│  Groq:   456 / 131K TPM      │
│  [██░░░░░░░░] 3%              │
│                               │
│  🔄 Agent Flow:               │
│  ┌───────────────────────┐    │
│  │  [ReactFlow Graph]    │    │
│  │                       │    │
│  │  Supervisor           │    │
│  │     │                 │    │
│  │     ▼                 │    │
│  │  CV Parser ✅          │    │
│  │     │                 │    │
│  │     ▼                 │    │
│  │  Job Hunter ✅         │    │
│  │     │                 │    │
│  │     ▼                 │    │
│  │  CV Tailor 🔄 ←(here) │    │
│  │     │                 │    │
│  │     ▼                 │    │
│  │  HR Finder ⏳         │    │
│  │     │                 │    │
│  │     ▼                 │    │
│  │  Email Sender ⏳      │    │
│  └───────────────────────┘    │
│                               │
│  📝 Execution Log:            │
│  ──────────────────           │
│  10:30:01 Supervisor routed   │
│           to CV Tailor        │
│  10:30:02 Extracting 23       │
│           keywords from JD    │
│  10:30:05 Mapped 18/23        │
│           requirements        │
│  10:30:08 Rewriting summary   │
│           for "Senior DevOps" │
│  10:30:12 Processing...       │
│                               │
│  [View Full Traces in         │
│   LangSmith →]                │
│  [View Analytics in           │
│   LangFuse →]                 │
└───────────────────────────────┘
```

**Settings / Integrations Page**
```
┌─────────────────────────────────────────────────────────┐
│  SETTINGS & INTEGRATIONS                                 │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  👤 PROFILE                                              │
│  ┌─────────────────────────────────────────────────────┐│
│  │  Name: Muhammad Ahmed                               ││
│  │  Email: ahmed@example.com                           ││
│  │  Default Role Target: DevOps Engineer               ││
│  │  Preferred Locations: NYC, Remote                   ││
│  │  [Edit Profile]                                     ││
│  └─────────────────────────────────────────────────────┘│
│                                                         │
│  🔗 CONNECTED SERVICES                                   │
│  ┌─────────────────────────────────────────────────────┐│
│  │  Gmail         🟢 Connected  [Disconnect]           ││
│  │  Google Drive   🟢 Connected  [Disconnect]          ││
│  │  Google Docs    🔴 Not Connected  [Connect]         ││
│  │  Supabase       🟢 Connected                        ││
│  │  Upstash Redis  🟢 Connected                        ││
│  └─────────────────────────────────────────────────────┘│
│                                                         │
│  📊 API QUOTA STATUS                                     │
│  ┌─────────────────────────────────────────────────────┐│
│  │  Gemini Flash   1234/1500 RPD  [████████░░] 82%     ││
│  │  Groq Llama     456/14400 RPD  [██░░░░░░░░] 3%     ││
│  │  SerpAPI        45/100 monthly [████░░░░░░] 45%     ││
│  │  Hunter.io      12/25 monthly  [████░░░░░░] 48%     ││
│  │  JSearch API    234/500 monthly[████░░░░░░] 47%     ││
│  │  Upstash Redis  4500/10K daily [████░░░░░░] 45%     ││
│  └─────────────────────────────────────────────────────┘│
│                                                         │
│  🔑 API KEYS (masked)                                    │
│  ┌─────────────────────────────────────────────────────┐│
│  │  Google AI:  sk-...4f2d  ✅ Valid  [Update]          ││
│  │  Groq:       gsk-...8a1e  ✅ Valid  [Update]         ││
│  │  SerpAPI:    abc-...9x2f  ✅ Valid  [Update]         ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

---

## 10. USER JOURNEY

### 10.1 First-Time User Journey

```
Step 1: SIGN UP
├── User visits Digital FTE website
├── Creates account (email + password)
└── Redirected to onboarding wizard

Step 2: CONNECT SERVICES
├── Prompted to connect Google Account
├── OAuth flow for Gmail + Drive permissions
└── Permissions explained clearly

Step 3: UPLOAD CV
├── Drag & drop or file picker (PDF/DOCX)
├── Upload to Supabase Storage
├── AI parsing begins immediately
├── Observability panel shows CV Parser Agent working
├── Parsed CV preview shown for verification
└── User confirms or edits parsed data

Step 4: SET PREFERENCES
├── Target job roles (can be multiple)
├── Preferred locations
├── Salary expectations
├── Remote/hybrid/onsite preference
└── Industries of interest

Step 5: FIRST JOB SEARCH
├── User types "Find me jobs" or clicks button
├── Agent flow visible in observability panel
├── 10 jobs returned in 15-30 seconds
├── Displayed as cards with match scores
└── User explores results

Step 6: FIRST CV TAILORING
├── User selects a job → clicks "Tailor CV"
├── CV Tailor Agent works (visible in panel)
├── Shows: keywords found, changes being made
├── Tailored CV preview (side-by-side comparison)
├── Match score shown (before vs after)
├── PDF generated and stored in Supabase Storage
└── Cover letter also generated

Step 7: FIRST APPLICATION
├── User clicks "Apply"
├── HR Finder Agent searches for contact
├── Email draft shown for review
├── User approves (or edits)
├── Email sent via Gmail API
└── Status tracked in Applications page

Step 8: INTERVIEW PREP (when called back)
├── User marks application as "Interview Scheduled"
├── Interview Prep Agent activates
├── Company research presented
├── Practice questions generated
├── Study materials (PPTX) created and stored in Supabase Storage
└── Optional: Mock interview chat session
```

### 10.2 Returning User Journey

```
Step 1: LOGIN → Dashboard
├── See latest stats: jobs found, apps sent, interviews
├── See recent activity feed
├── Notifications for any updates

Step 2: CHAT or DASHBOARD
├── "Find me 10 React Developer jobs in SF"
├── "Tailor my CV for all 10 jobs"
├── "Apply to the top 5"
├── "Prepare me for the Google interview"
├── Natural language commands processed by Supervisor Agent
```

---

## 11. OBSERVABILITY & MONITORING

### 11.1 LangSmith Integration

```yaml
langsmith_config:
  project_name: "digital-fte"
  tracing: true
  
  what_it_tracks:
    - Every LLM call (input, output, tokens, latency)
    - Chain/Agent execution traces
    - Tool invocations
    - Error traces with full context
    - Token costs per operation
  
  usage:
    - Debug agent behavior
    - Identify slow/expensive operations  
    - Compare prompt versions
    - Regression testing of agent outputs
  
  integration_code: |
    import os
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = "your_key"
    os.environ["LANGCHAIN_PROJECT"] = "digital-fte"
    # All LangChain/LangGraph calls automatically traced
```

### 11.2 LangFuse Integration

```yaml
langfuse_config:
  deployment: "Cloud (free tier) OR Self-hosted (Docker)"
  
  what_it_provides:
    - Cost analytics dashboard
    - Token usage over time
    - Latency percentiles
    - User-level analytics
    - Prompt management & versioning
    - Evaluation scoring
    - Session replay
  
  custom_events:
    - job_search_completed
    - cv_tailored
    - application_sent
    - interview_prep_generated
    - quota_limit_reached
    - model_fallback_triggered
  
  integration_code: |
    from langfuse.callback import CallbackHandler
    
    langfuse_handler = CallbackHandler(
        public_key="pk-...",
        secret_key="sk-...",
        host="https://cloud.langfuse.com"
    )
    
    # Pass as callback to LangChain/LangGraph
    result = chain.invoke(input, config={"callbacks": [langfuse_handler]})
```

### 11.3 Custom Real-Time Observability

```yaml
custom_observability:
  description: >
    Real-time agent status streamed to frontend via WebSocket.
    User sees exactly what each agent is doing at any moment.
  
  websocket_events:
    agent_started:
      data: {agent_name, plan, estimated_time}
    
    agent_progress:
      data: {agent_name, step, total_steps, current_action, details}
    
    agent_completed:
      data: {agent_name, result_summary, time_taken, tokens_used}
    
    agent_error:
      data: {agent_name, error_message, retry_count, fallback_action}
    
    model_switch:
      data: {from_model, to_model, reason}
    
    quota_warning:
      data: {provider, usage_percent, remaining}
    
    workflow_update:
      data: {graph_state, active_node, completed_nodes, pending_nodes}
  
  implementation:
    backend: "FastAPI WebSocket endpoint"
    frontend: "Socket.io client updating React state"
    middleware: "Upstash Redis Pub/Sub for multi-process support"
```

### 11.4 Observability Dashboard Metrics

```
METRICS TO DISPLAY:
├── Agent Performance
│   ├── Average execution time per agent
│   ├── Success/failure rate per agent
│   ├── Most active agents
│   └── Error frequency by agent
│
├── LLM Usage
│   ├── Tokens used (input/output) per model
│   ├── Cost estimation (even for free tier)
│   ├── Requests per minute/day per model
│   ├── Quota remaining visualization
│   └── Fallback frequency
│
├── Job Search Analytics
│   ├── Jobs found per search
│   ├── Average match score
│   ├── Source distribution (LinkedIn/Indeed/Glassdoor)
│   └── Most common missing skills
│
├── Application Analytics
│   ├── Applications sent over time
│   ├── Response rate (if trackable)
│   ├── Average CV match score of sent applications
│   └── HR contact find success rate
│
└── System Health
    ├── API endpoint response times
    ├── Supabase query performance
    ├── WebSocket connection count
    └── Background task queue depth
```

---

## 12. PROJECT STRUCTURE

```
digital-fte/
├── README.md
├── docker-compose.yml
├── .env.example
├── .gitignore
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── pyproject.toml
│   ├── alembic.ini
│   │
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI app entry
│   │   ├── config.py                  # Settings & env vars (pydantic-settings)
│   │   ├── worker.py                  # ARQ worker settings
│   │   │
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── deps.py                # Dependencies (DB, auth)
│   │   │   ├── router.py              # Main API router
│   │   │   │
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── auth.py            # Login, signup, OAuth
│   │   │   │   ├── cv.py              # CV upload, parse, list
│   │   │   │   ├── jobs.py            # Job search, list, details
│   │   │   │   ├── applications.py    # Apply, approve, track
│   │   │   │   ├── interview.py       # Interview prep
│   │   │   │   ├── chat.py            # Chat interface API
│   │   │   │   ├── integrations.py    # Google OAuth, connections
│   │   │   │   ├── observability.py   # Agent status, logs
│   │   │   │   └── dashboard.py       # Dashboard stats
│   │   │   │
│   │   │   └── websocket/
│   │   │       ├── __init__.py
│   │   │       └── handler.py         # WebSocket connection handler
│   │   │
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── graph.py               # LangGraph workflow definition
│   │   │   ├── state.py               # State schema definitions
│   │   │   ├── supervisor.py          # Supervisor agent
│   │   │   ├── cv_parser.py           # CV Parser agent
│   │   │   ├── job_hunter.py          # Job Hunter agent
│   │   │   ├── cv_tailor.py           # CV Tailor agent
│   │   │   ├── hr_finder.py           # HR Finder agent
│   │   │   ├── email_sender.py        # Email Sender agent
│   │   │   ├── interview_prep.py      # Interview Prep agent
│   │   │   ├── doc_generator.py       # Document Generator agent
│   │   │   │
│   │   │   ├── tools/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── job_search.py      # SerpAPI, JSearch tools
│   │   │   │   ├── web_scraper.py     # Playwright scraping
│   │   │   │   ├── email_tools.py     # Gmail API tools
│   │   │   │   ├── hr_lookup.py       # Hunter.io, Apollo tools
│   │   │   │   ├── pdf_tools.py       # PDF read/generate tools
│   │   │   │   ├── pptx_tools.py      # PPTX generation tools
│   │   │   │   ├── storage_tools.py   # Supabase Storage tools
│   │   │   │   ├── drive_tools.py     # Google Drive tools
│   │   │   │   └── embedding_tools.py # Embedding generation (pgvector)
│   │   │   │
│   │   │   └── prompts/
│   │   │       ├── __init__.py
│   │   │       ├── supervisor_prompts.py
│   │   │       ├── cv_parser_prompts.py
│   │   │       ├── cv_tailor_prompts.py
│   │   │       ├── job_hunter_prompts.py
│   │   │       ├── hr_finder_prompts.py
│   │   │       ├── email_prompts.py
│   │   │       └── interview_prompts.py
│   │   │
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── security.py            # JWT, hashing, auth
│   │   │   ├── llm_router.py          # LLM selection + fallback
│   │   │   ├── quota_manager.py       # API quota tracking (Upstash Redis)
│   │   │   ├── event_bus.py           # WebSocket event emitter
│   │   │   └── google_auth.py         # Google OAuth handler
│   │   │
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── database.py            # SQLAlchemy engine → Supabase PostgreSQL
│   │   │   ├── models.py              # ORM models (with pgvector columns)
│   │   │   ├── vector_store.py        # Supabase pgvector via vecs
│   │   │   ├── upstash_client.py      # Upstash Redis connection
│   │   │   └── supabase_client.py     # Supabase Storage + helpers
│   │   │
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── user.py                # User Pydantic schemas
│   │   │   ├── cv.py                  # CV schemas
│   │   │   ├── job.py                 # Job schemas
│   │   │   ├── application.py         # Application schemas
│   │   │   ├── chat.py                # Chat message schemas
│   │   │   └── agent.py               # Agent status schemas
│   │   │
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── cv_service.py          # CV business logic
│   │   │   ├── job_service.py         # Job business logic
│   │   │   ├── application_service.py # Application business logic
│   │   │   ├── chat_service.py        # Chat processing
│   │   │   └── integration_service.py # External service logic
│   │   │
│   │   ├── templates/
│   │   │   ├── cv/
│   │   │   │   ├── modern.html        # CV template 1
│   │   │   │   ├── classic.html       # CV template 2
│   │   │   │   └── minimal.html       # CV template 3
│   │   │   ├── email/
│   │   │   │   ├── application.html   # Job application email
│   │   │   │   └── follow_up.html     # Follow-up email
│   │   │   └── cv_styles.css          # CV styling
│   │   │
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── file_handler.py        # File upload/download (Supabase Storage)
│   │       ├── text_processor.py      # Text cleaning, extraction
│   │       └── scoring.py             # Match scoring algorithms
│   │
│   ├── migrations/
│   │   ├── versions/
│   │   │   └── 001_initial.py
│   │   └── env.py
│   │
│   └── tests/
│       ├── __init__.py
│       ├── test_agents/
│       ├── test_api/
│       └── test_services/
│
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── next.config.ts
│   │
│   ├── public/
│   │   └── assets/
│   │
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx             # Root layout
│   │   │   ├── page.tsx               # Landing/Login page
│   │   │   ├── globals.css
│   │   │   │
│   │   │   ├── (auth)/
│   │   │   │   ├── login/page.tsx
│   │   │   │   └── signup/page.tsx
│   │   │   │
│   │   │   └── (dashboard)/
│   │   │       ├── layout.tsx         # Dashboard layout (sidebar)
│   │   │       ├── dashboard/page.tsx # Main dashboard
│   │   │       ├── chat/page.tsx      # Chat interface
│   │   │       ├── jobs/
│   │   │       │   ├── page.tsx       # Jobs list
│   │   │       │   └── [id]/page.tsx  # Job detail
│   │   │       ├── cvs/
│   │   │       │   ├── page.tsx       # CV management
│   │   │       │   └── [id]/page.tsx  # CV detail/compare
│   │   │       ├── applications/
│   │   │       │   ├── page.tsx       # Applications list
│   │   │       │   └── [id]/page.tsx  # Application detail
│   │   │       ├── interview/
│   │   │       │   ├── page.tsx       # Interview prep list
│   │   │       │   └── [id]/page.tsx  # Prep detail/mock
│   │   │       └── settings/
│   │   │           └── page.tsx       # Settings + integrations
│   │   │
│   │   ├── components/
│   │   │   ├── ui/                    # shadcn/ui components
│   │   │   │   ├── button.tsx
│   │   │   │   ├── card.tsx
│   │   │   │   ├── dialog.tsx
│   │   │   │   ├── input.tsx
│   │   │   │   ├── badge.tsx
│   │   │   │   ├── progress.tsx
│   │   │   │   ├── tabs.tsx
│   │   │   │   ├── toast.tsx
│   │   │   │   └── ... (all shadcn components)
│   │   │   │
│   │   │   ├── layout/
│   │   │   │   ├── Sidebar.tsx
│   │   │   │   ├── Header.tsx
│   │   │   │   ├── ObservabilityPanel.tsx
│   │   │   │   └── StatusBar.tsx
│   │   │   │
│   │   │   ├── dashboard/
│   │   │   │   ├── StatsCards.tsx
│   │   │   │   ├── RecentActivity.tsx
│   │   │   │   ├── PipelineChart.tsx
│   │   │   │   └── QuickActions.tsx
│   │   │   │
│   │   │   ├── chat/
│   │   │   │   ├── ChatWindow.tsx
│   │   │   │   ├── ChatMessage.tsx
│   │   │   │   ├── ChatInput.tsx
│   │   │   │   ├── AgentStatusCard.tsx
│   │   │   │   └── JobCard.tsx
│   │   │   │
│   │   │   ├── jobs/
│   │   │   │   ├── JobList.tsx
│   │   │   │   ├── JobCard.tsx
│   │   │   │   ├── JobDetail.tsx
│   │   │   │   ├── MatchScore.tsx
│   │   │   │   └── SkillComparison.tsx
│   │   │   │
│   │   │   ├── cv/
│   │   │   │   ├── CVUploader.tsx
│   │   │   │   ├── CVPreview.tsx
│   │   │   │   ├── CVComparison.tsx
│   │   │   │   └── CVEditor.tsx
│   │   │   │
│   │   │   ├── applications/
│   │   │   │   ├── ApplicationList.tsx
│   │   │   │   ├── ApplicationCard.tsx
│   │   │   │   ├── EmailPreview.tsx
│   │   │   │   └── ApprovalDialog.tsx
│   │   │   │
│   │   │   ├── interview/
│   │   │   │   ├── PrepOverview.tsx
│   │   │   │   ├── QuestionCard.tsx
│   │   │   │   ├── MockInterview.tsx
│   │   │   │   └── CompanyResearch.tsx
│   │   │   │
│   │   │   └── observability/
│   │   │       ├── AgentFlow.tsx      # ReactFlow visualization
│   │   │       ├── AgentStatus.tsx
│   │   │       ├── ExecutionLog.tsx
│   │   │       ├── TokenUsage.tsx
│   │   │       └── QuotaMonitor.tsx
│   │   │
│   │   ├── hooks/
│   │   │   ├── useWebSocket.ts
│   │   │   ├── useChat.ts
│   │   │   ├── useAgentStatus.ts
│   │   │   └── useAuth.ts
│   │   │
│   │   ├── lib/
│   │   │   ├── api.ts                 # API client (fetch/axios)
│   │   │   ├── socket.ts             # WebSocket client
│   │   │   ├── supabase.ts           # Supabase browser client
│   │   │   └── utils.ts              # Utility functions
│   │   │
│   │   ├── stores/
│   │   │   ├── authStore.ts           # Zustand auth store
│   │   │   ├── chatStore.ts           # Chat state
│   │   │   ├── jobStore.ts            # Jobs state
│   │   │   └── agentStore.ts          # Agent observability state
│   │   │
│   │   └── types/
│   │       ├── index.ts
│   │       ├── cv.ts
│   │       ├── job.ts
│   │       ├── application.ts
│   │       └── agent.ts
│   │
│   └── tests/
│
├── scripts/
│   ├── setup.sh                       # Initial setup script
│   ├── seed_db.py                     # Seed database
│   ├── setup_supabase.sql             # SQL to run in Supabase Dashboard
│   └── test_agents.py                 # Test agent workflows
│
└── docs/
    ├── API.md                         # API documentation
    ├── AGENTS.md                      # Agent documentation
    ├── SETUP.md                       # Setup instructions
    └── ARCHITECTURE.md                # Architecture details
```

---

## 13. IMPLEMENTATION PHASES

### Phase 1: Foundation (Week 1-2)

```yaml
phase_1:
  name: "Foundation & Infrastructure"
  duration: "2 weeks"
  
  tasks:
    1.1_project_setup:
      - Initialize Git repository
      - Create project structure (as defined above)
      - Configure environment variables
      - Set up Python 3.13 virtual environment
      - Install all backend dependencies
      - Initialize Next.js 15 frontend with TypeScript
      - Install and configure shadcn/ui + Tailwind
    
    1.2_cloud_services_setup:
      - Create Supabase project (free tier)
      - Get Supabase URL, anon key, service role key
      - Get Supabase database connection strings (pooler + direct)
      - Enable pgvector extension in Supabase SQL Editor
      - Create Supabase Storage buckets (cvs, generated, templates)
      - Create Upstash Redis database (free tier)
      - Get Upstash Redis URL and REST credentials
      - Verify all cloud connections
    
    1.3_database_setup:
      - Create SQLAlchemy models (all tables including vector tables)
      - Configure Alembic for migrations (using Supabase direct URL)
      - Run initial migration against Supabase PostgreSQL
      - Run setup_supabase.sql for pgvector functions
      - Set up Upstash Redis connection
      - Set up Supabase pgvector via vecs client
    
    1.4_backend_api_skeleton:
      - Create FastAPI app with CORS
      - Implement JWT authentication (signup, login)
      - Create all API route files (empty handlers)
      - Set up WebSocket endpoint
      - Implement file upload endpoint (to Supabase Storage)
      - Create health check endpoint
    
    1.5_frontend_skeleton:
      - Create layout with sidebar navigation
      - Create all page files (empty)
      - Implement authentication pages (login/signup)
      - Set up Zustand stores
      - Configure API client
      - Set up Supabase browser client
      - Set up WebSocket client hook
    
    1.6_llm_setup:
      - Configure Gemini 2.0 Flash connection
      - Configure Groq connection (Llama 3.3, Mixtral)
      - Implement LLM Router with fallback logic
      - Implement quota manager (Upstash Redis-based)
      - Test all LLM connections
      - Set up LangSmith tracing
      - Set up LangFuse (cloud free tier)

  deliverables:
    - Cloud services configured (Supabase + Upstash)
    - Auth working (signup/login)
    - Empty but navigable frontend
    - All LLM connections verified
    - Database schema deployed to Supabase
    - Observability tools connected
```

### Phase 2: CV Intelligence (Week 3)

```yaml
phase_2:
  name: "CV Upload, Parse & Store"
  duration: "1 week"
  
  tasks:
    2.1_cv_upload:
      - Implement file upload API (PDF, DOCX)
      - Upload file to Supabase Storage (cvs bucket)
      - Create CV record in Supabase database
      - Frontend: CVUploader component with drag-drop
    
    2.2_cv_parser_agent:
      - Create CV Parser Agent with LangChain
      - PDF text extraction (pypdf + pdfplumber)
      - DOCX text extraction (python-docx)
      - LLM-powered structured data extraction
      - Prompt engineering for CV parsing
      - Extract: personal info, summary, skills,
        experience, education, projects, certifications
      - Store parsed data as JSONB in Supabase database
    
    2.3_cv_embeddings:
      - Generate embeddings for CV sections using sentence-transformers
      - Store in Supabase pgvector (cv_embeddings table)
      - Implement semantic search via match_cv_sections function
    
    2.4_cv_frontend:
      - CVPreview component (display parsed CV)
      - CV management page (list, view, delete)
      - Parsed data verification UI
      - Edit capability for parsed data
    
    2.5_observability:
      - Emit WebSocket events during parsing
      - Show parsing progress in Observability Panel
      - LangSmith traces for parser agent

  deliverables:
    - Upload CV → auto-parse → view structured data
    - Embeddings stored in Supabase pgvector
    - Files stored in Supabase Storage
    - Real-time parsing status visible in UI
```

### Phase 3: Job Hunting (Week 4)

```yaml
phase_3:
  name: "Job Search & Matching"
  duration: "1 week"
  
  tasks:
    3.1_job_search_tools:
      - Implement SerpAPI Google Jobs search tool
      - Implement RapidAPI JSearch tool
      - Implement Playwright web scraper (fallback)
      - Deduplication logic
      - Full job description fetching
    
    3.2_job_hunter_agent:
      - Create Job Hunter Agent with LangChain
      - Natural language query understanding
      - Multi-source parallel search
      - Result aggregation and dedup
      - Structured job data extraction
    
    3.3_job_matching:
      - Implement semantic matching (Supabase pgvector embeddings)
      - Keyword overlap scoring
      - Experience level matching
      - Composite match score calculation
      - Identify matching and missing skills
    
    3.4_job_storage:
      - Store jobs in Supabase database
      - Store job embeddings in Supabase pgvector (job_embeddings table)
    
    3.5_job_frontend:
      - JobList page with filters
      - JobCard component (match score, skills)
      - JobDetail page (full description)
      - SkillComparison component
      - MatchScore visual component (progress bar)
    
    3.6_chat_integration:
      - "Find me jobs" command in chat
      - Job results displayed as cards in chat
      - Quick action buttons on job cards

  deliverables:
    - "Find 10 DevOps jobs in NYC" → 10 ranked results
    - Match scores with skill analysis
    - Jobs browsable in dashboard and chat
```

### Phase 4: CV Tailoring Engine (Week 5-6)

```yaml
phase_4:
  name: "CV Customization & Generation"
  duration: "2 weeks"
  
  tasks:
    4.1_cv_tailor_agent:
      - Create CV Tailor Agent (most complex agent)
      - Job description deep analysis prompt
      - Keyword extraction from job description
      - Skill gap analysis logic
      - Professional summary rewriting prompt
      - Experience bullet rewriting prompt
      - Skills section optimization prompt
      - Cover letter generation prompt
      - ATS optimization pass prompt
      - Quality scoring logic
    
    4.2_prompt_engineering:
      - Craft and test all tailoring prompts
      - Ensure truthfulness preservation
      - Handle edge cases (career change, gaps, etc.)
      - Test across different role types
      - A/B test prompt variations
    
    4.3_document_generation:
      - Create HTML CV templates (3 styles)
      - CSS styling for professional look
      - WeasyPrint HTML → PDF conversion
      - Jinja2 template rendering
      - Cover letter PDF generation
      - Upload generated PDFs to Supabase Storage (generated bucket)
    
    4.4_comparison_ui:
      - CVComparison component (original vs tailored)
      - Side-by-side diff view
      - Changes highlighted
      - Match score before/after
      - Download tailored PDF button (from Supabase Storage)
    
    4.5_batch_tailoring:
      - Tailor CV for multiple jobs in batch
      - Queue management with ARQ + Upstash Redis
      - Progress tracking per job
      - Batch status in dashboard
    
    4.6_observability:
      - Detailed step-by-step tracking
      - "Rewriting experience section..."
      - "Optimizing for ATS..."
      - Token usage per tailoring operation

  deliverables:
    - Select job → get 100% tailored CV + cover letter
    - Professional PDF output stored in Supabase Storage
    - Visual comparison of changes
    - Batch tailoring for multiple jobs
```

### Phase 5: HR Contact & Application (Week 7)

```yaml
phase_5:
  name: "HR Finding & Email Application"
  duration: "1 week"
  
  tasks:
    5.1_hr_finder_agent:
      - Implement Hunter.io API integration
      - Implement Apollo.io API integration (optional)
      - Google search for hiring managers
      - Email pattern detection
      - Email verification
      - Confidence scoring
    
    5.2_email_sender_agent:
      - Google OAuth flow for Gmail access
      - Gmail API send email implementation
      - Email composition with LLM
      - PDF attachment handling (download from Supabase Storage)
      - Professional email templates
    
    5.3_approval_flow:
      - Human-in-the-loop approval gate
      - Email preview UI (ApprovalDialog)
      - Edit email before sending
      - Approve/Reject/Edit actions
      - Batch approval for multiple applications
    
    5.4_application_tracking:
      - Application status management
      - Status transitions (pending → sent → etc.)
      - Application list page
      - Application detail page
      - Status badges and timeline
    
    5.5_google_integration:
      - OAuth consent screen setup guide
      - Token management (refresh tokens)
      - Drive upload for generated CVs
      - Integration settings page

  deliverables:
    - Find HR → Draft email → User approves → Send via Gmail
    - Full application tracking pipeline
    - Google Drive integration for file storage
```

### Phase 6: Interview Preparation (Week 8)

```yaml
phase_6:
  name: "Interview Prep & Mock Interview"
  duration: "1 week"
  
  tasks:
    6.1_interview_prep_agent:
      - Company research via web search
      - Technical question generation
      - Behavioral question generation (STAR format)
      - Salary research compilation
      - Tips and recommendations
      - Company culture analysis
    
    6.2_study_materials:
      - PPTX slide generation (python-pptx)
      - PDF cheat sheet generation
      - Key points summary
      - Questions to ask interviewer
      - Upload materials to Supabase Storage
    
    6.3_mock_interview:
      - Chat-based mock interview flow
      - AI asks questions, user responds
      - AI provides feedback on answers
      - Score responses
      - Suggest improvements
    
    6.4_interview_frontend:
      - PrepOverview page
      - QuestionCard component (show/hide answers)
      - MockInterview chat interface
      - CompanyResearch component
      - Download materials buttons (from Supabase Storage)

  deliverables:
    - Complete interview prep package per job
    - Mock interview chat feature
    - Downloadable study materials (PPTX, PDF)
```

### Phase 7: LangGraph Orchestration (Week 9)

```yaml
phase_7:
  name: "Multi-Agent Orchestration with LangGraph"
  duration: "1 week"
  
  tasks:
    7.1_langgraph_workflow:
      - Define complete StateGraph
      - Implement Supervisor Agent routing logic
      - Wire all agents as graph nodes
      - Implement conditional edges
      - Human-in-the-loop node
      - Error handling and retry logic
      - State persistence (checkpoint via Upstash Redis)
    
    7.2_chat_orchestration:
      - Natural language intent detection
      - Route chat messages through Supervisor
      - Multi-turn conversation support
      - Context management across turns
      - Command parsing ("find jobs", "tailor cv", etc.)
    
    7.3_workflow_visualization:
      - ReactFlow graph showing current workflow
      - Active node highlighting
      - Completed/pending node status
      - Real-time updates via WebSocket
    
    7.4_error_recovery:
      - Agent retry with exponential backoff
      - Model fallback on failure
      - Graceful error messages to user
      - Partial result handling

  deliverables:
    - Full end-to-end automated pipeline
    - Chat-driven agent orchestration
    - Visual workflow in UI
    - Robust error handling
```

### Phase 8: Dashboard & Observability (Week 10)

```yaml
phase_8:
  name: "Dashboard, Analytics & Observability"
  duration: "1 week"
  
  tasks:
    8.1_dashboard:
      - Stats cards (CVs, Jobs, Apps, Interviews)
      - Recent activity feed
      - Application pipeline chart (Recharts)
      - Match score distribution chart
      - Quick action buttons
    
    8.2_observability_panel:
      - Real-time agent status display
      - Current plan step-by-step view
      - Execution time tracking
      - Token usage per agent
      - Model usage indicators
      - Error display
    
    8.3_agent_flow_visualization:
      - ReactFlow integration
      - Dynamic graph based on current session
      - Node status (active, complete, pending, error)
      - Click node to see details
    
    8.4_quota_dashboard:
      - Per-provider quota visualization
      - Warning indicators at 80%
      - Usage history chart
      - Model fallback log
      - Upstash Redis commands usage display
    
    8.5_langsmith_langfuse_links:
      - Deep links to LangSmith traces
      - Deep links to LangFuse analytics
      - Embedded LangFuse dashboard (iframe optional)

  deliverables:
    - Professional dashboard with real analytics
    - Full agent observability in real-time
    - Quota monitoring and warnings
```

### Phase 9: Polish & Testing (Week 11-12)

```yaml
phase_9:
  name: "Testing, Polish & Deployment"
  duration: "2 weeks"
  
  tasks:
    9.1_testing:
      - Unit tests for all agents
      - Unit tests for all API endpoints
      - Integration tests for workflows
      - End-to-end test: upload CV → find jobs → tailor → apply
      - Load testing for concurrent users
      - LLM response quality testing
    
    9.2_ui_polish:
      - Responsive design review
      - Dark/light mode
      - Loading states and skeletons
      - Error states and empty states
      - Toast notifications
      - Animations and transitions
      - Accessibility audit
    
    9.3_security:
      - Input sanitization
      - Rate limiting per user
      - API key encryption in DB
      - HTTPS enforcement
      - OAuth token security
      - SQL injection prevention (ORM)
      - XSS prevention
      - Supabase RLS (Row Level Security) policies
    
    9.4_documentation:
      - API documentation (auto-generated by FastAPI)
      - Agent documentation
      - Setup guide (including Supabase + Upstash setup)
      - User guide
    
    9.5_deployment:
      - Docker Compose production config
      - Environment variable documentation
      - Health check endpoints
      - Logging configuration
      - Backup strategy (Supabase handles DB backups)

  deliverables:
    - Production-ready application
    - Full test suite
    - Complete documentation
    - Deployment ready
```

---

## 14. ANTIGRAVITY EXECUTION INSTRUCTIONS

### 14.1 Execution Order

```markdown
# ANTIGRAVITY EXECUTION PLAN
# Execute in this exact order

## STEP 1: Set Up Cloud Services
- Create Supabase project at https://supabase.com (free tier)
- Note: Project URL, anon key, service role key, DB connection strings
- Create Upstash Redis database at https://upstash.com (free tier)
- Note: Redis URL, REST URL, REST token
- Run scripts/setup_supabase.sql in Supabase SQL Editor
- Create storage buckets in Supabase Dashboard

## STEP 2: Initialize Project
- Create the full directory structure as defined in Section 12
- Initialize git repository
- Create .env.example with all required variables
- Create docker-compose.yml (backend + frontend only, no DB containers)

## STEP 3: Backend Foundation
- Create requirements.txt with all packages from Section 5.3
- Create FastAPI main.py with CORS, middleware
- Create config.py reading all env vars (using pydantic-settings)
- Create database.py with SQLAlchemy async engine (Supabase pooler URL)
- Create all ORM models from Section 6.1 (including pgvector columns)
- Create Alembic config (using Supabase direct URL for migrations)
- Run initial migration against Supabase PostgreSQL
- Create upstash_client.py (Upstash Redis connection)
- Create supabase_client.py (Supabase Storage + helpers)
- Create vector_store.py (pgvector via vecs)
- Implement JWT auth (signup, login, token refresh)

## STEP 4: LLM Infrastructure
- Create llm_router.py with Gemini + Groq fallback
- Create quota_manager.py with Upstash Redis counters
- Configure LangSmith tracing
- Configure LangFuse callbacks
- Create event_bus.py for WebSocket events
- Test LLM connections

## STEP 5: Agents (one by one)
- Create state.py (LangGraph state schema)
- Create cv_parser.py agent + prompts
- Create job_hunter.py agent + tools + prompts
- Create cv_tailor.py agent + prompts (most complex)
- Create hr_finder.py agent + tools + prompts
- Create email_sender.py agent + Gmail tools
- Create interview_prep.py agent + prompts
- Create doc_generator.py agent + PDF/PPTX tools + Supabase Storage
- Create supervisor.py agent + routing logic
- Create graph.py (LangGraph StateGraph wiring all agents)

## STEP 6: API Routes
- Create all route handlers calling agents/services
- Create WebSocket handler for real-time updates
- Create service layer for business logic
- Create Pydantic schemas for all request/response

## STEP 7: Frontend
- Initialize Next.js 15 with TypeScript
- Install and configure shadcn/ui (npx shadcn@latest init)
- Install Tailwind CSS
- Create layout with sidebar
- Create all pages (dashboard, chat, jobs, cvs,
  applications, interview, settings)
- Create all components as defined in Section 12
- Create Zustand stores
- Create API client, WebSocket hook, and Supabase browser client
- Wire everything together

## STEP 8: Integration Testing
- Test full pipeline end-to-end
- Fix bugs and edge cases
- Performance optimization

## STEP 9: Docker & Deployment
- Create Dockerfiles for backend and frontend
- Create production docker-compose (no DB/Redis containers needed)
- Final testing
```

### 14.2 Key Implementation Notes for Antigravity

```markdown
# CRITICAL IMPLEMENTATION NOTES

1. LLM CALLS: Always wrap in try/except with fallback
   - Try Gemini first
   - Catch rate limit → switch to Groq Llama
   - Catch again → switch to Mixtral
   - Log every switch

2. AGENT OBSERVABILITY: Every agent function should:
   - Emit "agent_started" event at beginning
   - Emit "agent_progress" events during execution
   - Emit "agent_completed" event at end
   - All via WebSocket through event_bus

3. LANGGRAPH STATE: Use TypedDict with clear types
   - Every field has a default
   - State is serializable (for Upstash Redis persistence)
   - State changes are logged

4. PROMPTS: Store all prompts in separate files
   - Use LangChain PromptTemplate
   - Include few-shot examples where needed
   - Version prompts in LangFuse

5. FREE TIER MANAGEMENT:
   - Check quota BEFORE every API call
   - Track in Upstash Redis with atomic increments
   - Show warnings in UI at 80%
   - Never crash on quota exceeded
   - Monitor Upstash Redis commands/day (10K limit)

6. HUMAN IN THE LOOP:
   - Email sending ALWAYS requires user approval
   - Show full preview before any external action
   - Allow editing before approval
   - Log all approvals/rejections

7. CV TAILORING TRUTH RULE:
   - NEVER fabricate experience or skills
   - Only reframe, reorder, emphasize existing data
   - Always note what was changed and why
   - User can review all changes

8. ERROR HANDLING:
   - Every agent has graceful failure mode
   - Partial results are saved (don't lose work)
   - User gets clear error messages
   - Automatic retry with backoff

9. FILE GENERATION & STORAGE:
   - CVs: HTML → CSS → WeasyPrint → PDF
   - Use Jinja2 templates for CV HTML
   - PPTX: python-pptx with clean templates
   - All files uploaded to Supabase Storage (cvs/generated buckets)
   - Optionally also to Google Drive
   - Use signed URLs for secure file access

10. WEBSOCKET PROTOCOL:
    - Frontend connects on login
    - Backend pushes events per session
    - Reconnection handling
    - Event types clearly defined

11. SUPABASE SPECIFIC:
    - Use connection pooler URL (port 6543) for app connections
    - Use direct URL (port 5432) for Alembic migrations
    - Enable RLS policies for security
    - Use Supabase Storage signed URLs for file downloads
    - pgvector indexes need enough data before creation (use ivfflat)

12. UPSTASH REDIS SPECIFIC:
    - Free tier: 10K commands/day — optimize usage
    - Use pipelines to batch commands
    - Use hset/hgetall instead of multiple set/get
    - Consider FastAPI BackgroundTasks for simple async work
    - Use ARQ instead of Celery (lighter Redis usage)
```

### 14.3 Environment Setup Script

```bash
#!/bin/bash
# scripts/setup.sh

set -e

echo "🚀 Setting up Digital FTE..."
echo ""

# ============================================================
# PRE-REQUISITES CHECK
# ============================================================
echo "📋 Checking prerequisites..."

command -v python3.13 >/dev/null 2>&1 || command -v python3 >/dev/null 2>&1 || { echo "❌ Python 3.13 required."; exit 1; }
command -v node >/dev/null 2>&1 || { echo "❌ Node.js required."; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "❌ npm required."; exit 1; }

echo "✅ Prerequisites OK"
echo ""

# ============================================================
# CLOUD SERVICES CHECK
# ============================================================
echo "☁️  Ensure cloud services are set up before continuing:"
echo ""
echo "  1. SUPABASE (https://supabase.com)"
echo "     - Create project → Get URL, anon key, service role key"
echo "     - Get database connection strings"
echo "     - Run scripts/setup_supabase.sql in SQL Editor"
echo ""
echo "  2. UPSTASH REDIS (https://upstash.com)"
echo "     - Create Redis database → Get URL and REST credentials"
echo ""
echo "  3. Copy .env.example → .env and fill in ALL values"
echo ""

if [ ! -f .env ]; then
    echo "❌ .env file not found! Copy .env.example to .env first."
    echo "   cp .env.example .env"
    exit 1
fi

echo "✅ .env file found"
echo ""

# Create directories
mkdir -p uploads generated logs

# Backend setup
echo "🐍 Setting up Python backend..."
cd backend
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Install Playwright browsers (for web scraping)
echo "🌐 Installing Playwright Chromium..."
playwright install chromium

# Download embedding model
echo "🧠 Downloading embedding model..."
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2'); print('✅ Model downloaded')"

cd ..

# Run database migrations against Supabase
echo "🗄️  Running database migrations..."
cd backend
source venv/bin/activate
alembic upgrade head
echo "✅ Migrations complete"
cd ..

# Frontend setup
echo "⚛️  Setting up Next.js 15 frontend..."
cd frontend
npm install
npx shadcn@latest init -y
npx shadcn@latest add button card dialog input badge progress tabs toast \
    dropdown-menu avatar separator sheet scroll-area select textarea \
    tooltip popover command table skeleton alert alert-dialog
cd ..

# Verify connections
echo "🔌 Verifying cloud connections..."
cd backend
source venv/bin/activate

python -c "
import os
from dotenv import load_dotenv
load_dotenv('../.env')

print('Testing Supabase...')
from supabase import create_client
sb = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_ROLE_KEY'])
print('  ✅ Supabase connected')

print('Testing Upstash Redis...')
import redis
r = redis.from_url(os.environ['UPSTASH_REDIS_URL'], ssl_cert_reqs=None)
r.ping()
print('  ✅ Upstash Redis connected')

print('Testing Gemini...')
import google.generativeai as genai
genai.configure(api_key=os.environ['GOOGLE_AI_API_KEY'])
model = genai.GenerativeModel('gemini-2.0-flash')
response = model.generate_content('Say hello in 3 words')
print(f'  ✅ Gemini connected: {response.text.strip()[:50]}')

print('')
print('🎉 All connections verified!')
"

cd ..

echo ""
echo "═══════════════════════════════════════════════════"
echo "  ✅ Digital FTE setup complete!"
echo "═══════════════════════════════════════════════════"
echo ""
echo "  To start the application:"
echo ""
echo "  Backend:  cd backend && source venv/bin/activate && uvicorn app.main:app --reload --port 8080"
echo "  Frontend: cd frontend && npm run dev"
echo ""
echo "  Or with Docker: docker compose up"
echo ""
echo "  📝 Remaining manual steps:"
echo "     1. Set up Google Cloud OAuth (for Gmail/Drive)"
echo "     2. Get SerpAPI key for job search"
echo "     3. Get Hunter.io key for HR contact finding"
echo "     4. Set up LangSmith account for tracing"
echo ""
```

### 14.4 Docker Compose

```yaml
# docker-compose.yml
# No database containers needed — using Supabase + Upstash cloud services

services:
  backend:
    build: ./backend
    ports:
      - "8080:8080"
    env_file:
      - .env
    volumes:
      - ./uploads:/app/uploads
      - ./generated:/app/generated
    command: uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      backend:
        condition: service_healthy
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8080
      - NEXT_PUBLIC_WS_URL=ws://localhost:8080
      - NEXT_PUBLIC_SUPABASE_URL=${SUPABASE_URL}
      - NEXT_PUBLIC_SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY}
    command: npm run dev

  worker:
    build: ./backend
    env_file:
      - .env
    depends_on:
      backend:
        condition: service_healthy
    command: arq app.worker.WorkerSettings
```

---

## SUMMARY

```
┌────────────────────────────────────────────────────────┐
│              DIGITAL FTE - PROJECT SUMMARY              │
├────────────────────────────────────────────────────────┤
│                                                        │
│  🏗️  Architecture: Multi-Agent AI System               │
│  🤖  Agents: 8 specialized + 1 supervisor              │
│  🧠  LLMs: Gemini Flash + Groq (free tier)             │
│  🔗  Orchestration: LangGraph + LangChain              │
│  📊  Observability: LangSmith + LangFuse               │
│  🖥️  Frontend: Next.js 15 + shadcn/ui                  │
│  ⚙️  Backend: FastAPI + Python 3.13                     │
│  🗄️  Database: Supabase (managed PostgreSQL)            │
│  🔍  Vectors: Supabase pgvector                        │
│  ⚡  Cache: Upstash Redis (cloud)                      │
│  📦  Storage: Supabase Storage                         │
│  📁  Files: WeasyPrint (PDF) + python-pptx              │
│  📧  Email: Gmail API                                   │
│  🔍  Jobs: SerpAPI + RapidAPI JSearch                   │
│  👤  HR: Hunter.io + Apollo.io                          │
│  🐳  Deploy: Docker Compose (simplified)                │
│  📅  Timeline: 12 weeks                                 │
│  💰  Cost: $0 (all free tier APIs + cloud)              │
│                                                        │
│  CLOUD SERVICES (Free Tier):                           │
│  ├─ Supabase: 500MB DB + pgvector + 1GB Storage       │
│  ├─ Upstash Redis: 10K commands/day, 256MB             │
│  ├─ LangSmith: 5K traces/month                         │
│  └─ LangFuse: 50K observations/month                   │
│                                                        │
│  FLOW: Upload CV → Find Jobs → Tailor CV →             │
│        Find HR → Send Email → Prep Interview           │
│                                                        │
│  ALL with full observability, real-time tracking,       │
│  human approval gates, and expandable architecture.    │
│                                                        │
└────────────────────────────────────────────────────────┘
```

---

## APPENDIX: HOW TO CONNECT CLOUD SERVICES

### A. Supabase Setup (Step by Step)

```
1. Go to https://supabase.com → Sign Up (GitHub or email)

2. Click "New Project"
   - Name: digital-fte
   - Password: <choose strong password, SAVE IT>
   - Region: <nearest to you>
   - Click "Create new project" → Wait 2 min

3. Get API Credentials (Settings → API):
   - SUPABASE_URL = Project URL
   - SUPABASE_ANON_KEY = anon/public key
   - SUPABASE_SERVICE_ROLE_KEY = service_role key

4. Get Database Connection Strings (Settings → Database):
   - DATABASE_URL (Transaction/Session pooler, port 6543)
     = postgresql+asyncpg://postgres.<ref>:<pass>@aws-0-<region>.pooler.supabase.com:6543/postgres
   - DIRECT_DATABASE_URL (Direct, port 5432)
     = postgresql://postgres.<ref>:<pass>@aws-0-<region>.pooler.supabase.com:5432/postgres

5. Enable pgvector (SQL Editor → New Query → Run):
   CREATE EXTENSION IF NOT EXISTS vector;

6. Create Storage Buckets (Storage → New Bucket):
   - "cvs" (Private)
   - "generated" (Private)
   - "templates" (Public)

7. Run full schema (SQL Editor):
   Copy and paste Section 6.1 SQL
```

### B. Upstash Redis Setup (Step by Step)

```
1. Go to https://upstash.com → Sign Up (GitHub, Google, or email)

2. Click "Create Database"
   - Name: digital-fte-cache
   - Type: Regional
   - Region: <nearest to your server>
   - TLS: Enabled
   - Eviction: Enabled
   - Click "Create"

3. Get Credentials (Database Details page):
   - UPSTASH_REDIS_URL = rediss://default:<password>@<endpoint>.upstash.io:6379
   - UPSTASH_REDIS_REST_URL = https://<endpoint>.upstash.io
   - UPSTASH_REDIS_REST_TOKEN = AXxxxxxxxxxxxxxxx

4. Test Connection (Python):
   import redis
   r = redis.from_url("rediss://default:xxx@xxx.upstash.io:6379", ssl_cert_reqs=None)
   r.ping()  # Should return True

5. Note Free Tier Limits:
   - 10,000 commands/day
   - 256 MB storage
   - 100 concurrent connections
```

### C. Backend Connection Code

```python
# backend/app/db/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
)

AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
```

```python
# backend/app/db/vector_store.py
import vecs
from sentence_transformers import SentenceTransformer
from app.config import settings

embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
vx = vecs.create_client(settings.DIRECT_DATABASE_URL)

cv_collection = vx.get_or_create_collection(name="cv_embeddings", dimension=384)
job_collection = vx.get_or_create_collection(name="job_embeddings", dimension=384)

def generate_embedding(text: str) -> list[float]:
    return embedding_model.encode(text).tolist()

def upsert_cv_embedding(cv_id: str, section: str, content: str, metadata: dict):
    embedding = generate_embedding(content)
    cv_collection.upsert(records=[
        (f"{cv_id}_{section}", embedding,
         {**metadata, "cv_id": cv_id, "section": section, "content": content})
    ])

def search_similar_jobs(query_text: str, top_k: int = 10) -> list:
    query_embedding = generate_embedding(query_text)
    return job_collection.query(data=query_embedding, limit=top_k,
                                include_metadata=True, include_value=True)
```

```python
# backend/app/db/upstash_client.py
import redis.asyncio as aioredis
from upstash_redis import Redis as UpstashRedis
from app.config import settings

redis_client = aioredis.from_url(
    settings.UPSTASH_REDIS_URL,
    encoding="utf-8", decode_responses=True, ssl_cert_reqs=None,
)

upstash_redis = UpstashRedis(
    url=settings.UPSTASH_REDIS_REST_URL,
    token=settings.UPSTASH_REDIS_REST_TOKEN,
)

async def get_quota_usage(provider: str, model: str, period: str) -> int:
    key = f"quota:{provider}:{model}:{period}"
    value = await redis_client.get(key)
    return int(value) if value else 0

async def increment_quota(provider: str, model: str, period: str,
                          amount: int = 1, ttl: int = 60):
    key = f"quota:{provider}:{model}:{period}"
    pipe = redis_client.pipeline()
    pipe.incrby(key, amount)
    pipe.expire(key, ttl)
    await pipe.execute()

async def set_agent_status(session_id: str, status_data: dict, ttl: int = 3600):
    key = f"agent_status:{session_id}"
    await redis_client.hset(key, mapping=status_data)
    await redis_client.expire(key, ttl)

async def get_agent_status(session_id: str) -> dict:
    return await redis_client.hgetall(f"agent_status:{session_id}")
```

```python
# backend/app/db/supabase_client.py
from supabase import create_client, Client
from app.config import settings

supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

async def upload_file(bucket: str, path: str, file_bytes: bytes, content_type: str):
    return supabase.storage.from_(bucket).upload(
        path=path, file=file_bytes,
        file_options={"content-type": content_type}
    )

def get_file_url(bucket: str, path: str) -> str:
    response = supabase.storage.from_(bucket).create_signed_url(path=path, expires_in=3600)
    return response["signedURL"]

async def download_file(bucket: str, path: str) -> bytes:
    return supabase.storage.from_(bucket).download(path)
```

```python
# backend/app/config.py
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str

    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    DATABASE_URL: str
    DIRECT_DATABASE_URL: str

    UPSTASH_REDIS_URL: str
    UPSTASH_REDIS_REST_URL: str
    UPSTASH_REDIS_REST_TOKEN: str

    GOOGLE_AI_API_KEY: str
    GROQ_API_KEY: str
    SERPAPI_API_KEY: str = ""
    RAPIDAPI_KEY: str = ""
    HUNTER_API_KEY: str = ""

    GOOGLE_CLOUD_PROJECT_ID: str = ""
    GOOGLE_OAUTH_CLIENT_ID: str = ""
    GOOGLE_OAUTH_CLIENT_SECRET: str = ""
    GOOGLE_CREDENTIALS_PATH: str = "./credentials.json"

    LANGCHAIN_TRACING_V2: bool = True
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_PROJECT: str = "digital-fte"
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"

    UPLOAD_DIR: str = "./uploads"
    GENERATED_DIR: str = "./generated"

    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
```

```typescript
// frontend/src/lib/supabase.ts
import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

export const supabase = createClient(supabaseUrl, supabaseAnonKey)
```

```typescript
// frontend/next.config.ts
import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      { source: '/api/:path*', destination: 'http://localhost:8080/:path*' },
    ]
  },
  images: {
    remotePatterns: [
      { protocol: 'https', hostname: '*.supabase.co' },
    ],
  },
}

export default nextConfig
```