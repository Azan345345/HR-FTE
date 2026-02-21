TABLE OF CONTENTS

1.  EXECUTIVE SUMMARY
2.  BUSINESS REQUIREMENTS
3.  SYSTEM ARCHITECTURE
4.  MULTI-AGENT DESIGN
5.  TECHNICAL STACK
6.  DATABASE DESIGN
7.  API KEYS & INTEGRATIONS
8.  WORKFLOWS (DETAILED)
9.  UI/UX DESIGN
10. USER JOURNEY
11. OBSERVABILITY & MONITORING
12. PROJECT STRUCTURE
13. IMPLEMENTATION PHASES
14. ANTIGRAVITY EXECUTION INSTRUCTIONS


1. EXECUTIVE SUMMARY
Digital FTE is an AI-powered multi-agent system that acts as a full-time employee dedicated to a candidate's job search. It ingests a CV, finds matching jobs across major platforms, rewrites the CV to match each job posting at 100%, extracts HR contact information, sends tailored applications via email, and prepares the candidate for interviews — all orchestrated through an intelligent agent pipeline with full observability.

2. BUSINESS REQUIREMENTS
2.1 Functional Requirements
text

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
2.2 Non-Functional Requirements
text

NFR-001  | Response time < 30s for job search
NFR-002  | System handles 100 concurrent users
NFR-003  | 99.5% uptime
NFR-004  | All data encrypted at rest and in transit
NFR-005  | GDPR compliant data handling
NFR-006  | Modular architecture for easy expansion
NFR-007  | Rate limiting for free-tier API quota protection
NFR-008  | Graceful degradation when API limits hit
2.3 Business Rules
text

BR-001   | Maximum 10 jobs fetched per single request
BR-002   | Each job gets a uniquely customized CV
BR-003   | CV customization must preserve truthful information
         | (enhance presentation, not fabricate)
BR-004   | Email sending requires user approval before dispatch
BR-005   | Interview prep adapts to specific company + role
BR-006   | Free-tier quota tracked and user warned at 80% usage
BR-007   | All agent actions are logged and auditable
3. SYSTEM ARCHITECTURE
3.1 High-Level Architecture
text

┌─────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Next.js 14)                       │
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
│  │Groq - Mixtral  │   │  │  │python-   │ │Hunter.io/│ │Chromium  │ │
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
│                      DATA LAYER                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │  PostgreSQL   │  │  Redis       │  │  ChromaDB / Qdrant       │  │
│  │  (Primary DB) │  │  (Cache +    │  │  (Vector Store for       │  │
│  │               │  │   Queue)     │  │   CV + Job Embeddings)   │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
│  ┌──────────────┐  ┌──────────────┐                                 │
│  │  MinIO/S3     │  │  SQLite      │                                │
│  │  (File Store) │  │  (Dev/Local) │                                │
│  └──────────────┘  └──────────────┘                                 │
└─────────────────────────────────────────────────────────────────────┘
3.2 Data Flow Architecture
text

User uploads CV
       │
       ▼
┌─────────────┐     ┌──────────────┐     ┌────────────────┐
│ CV Parser   │────▶│ CV Vector    │────▶│ Skill Extractor│
│ Agent       │     │ Store        │     │                │
└─────────────┘     └──────────────┘     └───────┬────────┘
                                                  │
       ┌──────────────────────────────────────────┘
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
4. MULTI-AGENT DESIGN
4.1 Agent Definitions
YAML

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
      Uploads to Google Drive if connected.
    framework: LangChain + LangGraph node
    llm: groq-llama3.3-70b
    tools: [weasyprint, reportlab, python_pptx, google_drive_api]
4.2 LangGraph State Machine
Python

# Conceptual State Graph Definition

from langgraph.graph import StateGraph, END
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
workflow.set_entry_point("supervisor")

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
4.3 Agent Communication Protocol
text

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
5. TECHNICAL STACK
5.1 Languages & Frameworks
YAML

backend:
  language: Python 3.12
  web_framework: FastAPI
  async: asyncio + uvicorn
  task_queue: Celery + Redis (for long-running agent tasks)

ai_orchestration:
  agent_framework: LangGraph (v0.2+)
  chain_framework: LangChain (v0.3+)
  tracing: LangSmith
  analytics: LangFuse
  embeddings: sentence-transformers (all-MiniLM-L6-v2) # free, local

frontend:
  framework: Next.js 14 (App Router)
  language: TypeScript
  ui_library: shadcn/ui + Tailwind CSS
  state_management: Zustand
  real_time: Socket.io
  charts: Recharts
  flow_visualization: ReactFlow (for agent workflow display)

database:
  primary: PostgreSQL 16
  cache: Redis 7
  vector_store: ChromaDB (local, free) OR Qdrant
  file_storage: Local filesystem + Google Drive API
  orm: SQLAlchemy 2.0 + Alembic (migrations)

devops:
  containerization: Docker + Docker Compose
  ci_cd: GitHub Actions
  env_management: python-dotenv
5.2 LLM Configuration (All Free Tier)
YAML

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
    Track usage per model per day in Redis.
  implementation:
    - Track token count per model per minute/day in Redis
    - Before each call, check remaining quota
    - If < 20% remaining, switch to fallback
    - Log all switches for observability
    - Reset counters daily at midnight UTC
5.3 Key Python Packages
txt

# requirements.txt

# Web Framework
fastapi==0.115.0
uvicorn[standard]==0.30.0
python-multipart==0.0.9
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4

# AI/LLM
langchain==0.3.7
langchain-core==0.3.15
langchain-community==0.3.5
langchain-google-genai==2.0.4
langchain-groq==0.2.1
langgraph==0.2.34
langsmith==0.1.137
langfuse==2.51.3

# Embeddings
sentence-transformers==3.2.0
chromadb==0.5.15

# Document Processing
PyPDF2==3.0.1
python-docx==1.1.0
pdfplumber==0.11.0

# Document Generation
weasyprint==62.3
reportlab==4.2.0
python-pptx==1.0.0
jinja2==3.1.4
markdown==3.7

# Job Search
serpapi==0.1.5
# OR
google-search-results==2.4.2

# Google Cloud
google-auth==2.35.0
google-auth-oauthlib==1.2.1
google-api-python-client==2.149.0
google-auth-httplib2==0.2.0

# Email
# (using Gmail API - included in google-api-python-client)

# HR Contact Finding
requests==2.32.0
beautifulsoup4==4.12.3
playwright==1.48.0  # for dynamic page scraping

# Database
sqlalchemy==2.0.35
alembic==1.13.3
asyncpg==0.30.0
psycopg2-binary==2.9.9
redis==5.2.0

# Task Queue
celery==5.4.0

# Utilities
pydantic==2.9.0
python-dotenv==1.0.1
httpx==0.27.0
tenacity==9.0.0  # retry logic
structlog==24.4.0  # structured logging

# WebSocket
websockets==13.0

# Testing
pytest==8.3.0
pytest-asyncio==0.24.0
6. DATABASE DESIGN
6.1 PostgreSQL Schema
SQL

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
    file_path TEXT NOT NULL,
    file_type VARCHAR(10) NOT NULL, -- pdf, docx
    parsed_data JSONB NOT NULL,     -- structured CV data
    raw_text TEXT,
    embedding_id VARCHAR(255),      -- reference to vector store
    is_primary BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

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
    external_id VARCHAR(255),       -- ID from source platform
    title VARCHAR(255) NOT NULL,
    company VARCHAR(255) NOT NULL,
    location VARCHAR(255),
    salary_range VARCHAR(100),
    job_type VARCHAR(50),
    description TEXT NOT NULL,
    requirements JSONB,             -- list of requirements
    nice_to_have JSONB,
    responsibilities JSONB,
    posted_date DATE,
    application_url TEXT,
    source VARCHAR(50) NOT NULL,    -- linkedin, indeed, glassdoor
    match_score FLOAT,
    matching_skills JSONB,
    missing_skills JSONB,
    raw_data JSONB,                 -- full scraped data
    created_at TIMESTAMP DEFAULT NOW()
);

-- Tailored CVs generated per job
CREATE TABLE tailored_cvs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    original_cv_id UUID REFERENCES user_cvs(id),
    job_id UUID REFERENCES jobs(id) ON DELETE CASCADE,
    tailored_data JSONB NOT NULL,   -- structured tailored CV
    pdf_path TEXT,
    cover_letter TEXT,
    ats_score FLOAT,                -- ATS compatibility score
    match_score FLOAT,              -- match against job desc
    changes_made JSONB,             -- what was changed and why
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
    confidence_score FLOAT,         -- 0-1 confidence in email
    source VARCHAR(100),            -- hunter.io, apollo, scraped
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
    study_material_path TEXT,       -- PPTX file path
    prep_score FLOAT,               -- readiness score
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
    plan TEXT,                       -- agent's plan before execution
    input_data JSONB,
    output_data JSONB,
    llm_model VARCHAR(100),
    tokens_input INT,
    tokens_output INT,
    execution_time_ms INT,
    status VARCHAR(50),             -- started, completed, failed, retrying
    error_message TEXT,
    trace_id VARCHAR(255),          -- LangSmith trace ID
    langfuse_trace_id VARCHAR(255),
    parent_execution_id UUID REFERENCES agent_executions(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- API quota tracking
CREATE TABLE api_quota_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider VARCHAR(100) NOT NULL, -- gemini, groq, serpapi, etc.
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
    role VARCHAR(20) NOT NULL,      -- user, assistant, system, agent
    agent_name VARCHAR(100),        -- which agent responded
    content TEXT NOT NULL,
    metadata JSONB,                 -- attachments, actions, etc.
    created_at TIMESTAMP DEFAULT NOW()
);

-- Connected external services
CREATE TABLE user_integrations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    service_name VARCHAR(100) NOT NULL, -- gmail, drive, docs
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
6.2 Redis Schema
YAML

redis_keys:
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
  "celery:*": 
    type: various (managed by Celery)

  # WebSocket channel mapping
  "ws:{user_id}": 
    type: string
    value: "connection_id"
    ttl: 3600
6.3 ChromaDB / Vector Store Schema
YAML

collections:
  user_cvs:
    description: "Embedded CV sections for semantic matching"
    metadata_schema:
      user_id: string
      cv_id: string
      section: string  # summary, experience, skills, education
      content: string

  job_descriptions:
    description: "Embedded job descriptions for matching"
    metadata_schema:
      job_id: string
      search_id: string
      title: string
      company: string
      source: string
7. API KEYS & INTEGRATIONS
7.1 Required API Keys
YAML

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
    
  # Browserless (for web scraping)
  # Can use Playwright locally instead (free)
7.2 Environment Configuration
env

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

# ========== DATABASE ==========
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/digital_fte
REDIS_URL=redis://localhost:6379/0

# ========== OBSERVABILITY ==========
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_key
LANGCHAIN_PROJECT=digital-fte

LANGFUSE_PUBLIC_KEY=your_langfuse_public_key
LANGFUSE_SECRET_KEY=your_langfuse_secret_key
LANGFUSE_HOST=https://cloud.langfuse.com
# OR for self-hosted:
# LANGFUSE_HOST=http://localhost:3001

# ========== APP CONFIG ==========
SECRET_KEY=your_jwt_secret_key
APP_ENV=development
LOG_LEVEL=DEBUG
UPLOAD_DIR=./uploads
GENERATED_DIR=./generated
8. WORKFLOWS (DETAILED)
8.1 Master Workflow
text

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
                                    │ in DB + Vector    │
                                    │ Store             │
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
  Store: tailored CV data + PDF in DB

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
  Store: HR name, email, confidence in DB

PHASE 5: APPLICATION SENDING
═════════════════════════════
For each job application:
       │
       ▼
  Email Sender Agent composes email:
    - Personalized subject line
    - Professional cover email body
    - Attached: tailored CV PDF
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
  All materials stored and accessible in dashboard
8.2 LangGraph Workflow (Detailed)
Python

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
8.3 Job Search Sub-Workflow
text

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
│     ├─ Semantic similarity (embeddings)                  │
│     ├─ Keyword overlap percentage                        │
│     ├─ Experience level match                            │
│     └─ Composite score 0-100                             │
│                                                          │
│  6. RANK AND RETURN TOP 10                               │
│     └─ Sorted by match_score descending                  │
│                                                          │
│  Output: List[Job] with full data + match analysis       │
└──────────────────────────────────────────────────────────┘
8.4 CV Tailoring Sub-Workflow
text

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
9. UI/UX DESIGN
9.1 Design System
YAML

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
9.2 Page Structure
text

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
9.3 Page Designs
Dashboard Page
text

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
Chat Interface Page
text

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
Jobs Page
text

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
Observability Panel (Right Side)
text

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
Settings / Integrations Page
text

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
│  │  Gmail      🟢 Connected  [Disconnect]              ││
│  │  Google Drive  🟢 Connected  [Disconnect]           ││
│  │  Google Docs   🔴 Not Connected  [Connect]          ││
│  └─────────────────────────────────────────────────────┘│
│                                                         │
│  📊 API QUOTA STATUS                                     │
│  ┌─────────────────────────────────────────────────────┐│
│  │  Gemini Flash   1234/1500 RPD  [████████░░] 82%     ││
│  │  Groq Llama     456/14400 RPD  [██░░░░░░░░] 3%     ││
│  │  SerpAPI        45/100 monthly [████░░░░░░] 45%     ││
│  │  Hunter.io      12/25 monthly  [████░░░░░░] 48%     ││
│  │  JSearch API    234/500 monthly[████░░░░░░] 47%     ││
│  └─────────────────────────────────────────────────────┘│
│                                                         │
│  🔑 API KEYS (masked)                                    │
│  ┌─────────────────────────────────────────────────────┐│
│  │  Google AI:  sk-...4f2d  ✅ Valid  [Update]          ││
│  │  Groq:       gsk-...8a1e  ✅ Valid  [Update]         ││
│  │  SerpAPI:    abc-...9x2f  ✅ Valid  [Update]         ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
10. USER JOURNEY
10.1 First-Time User Journey
text

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
├── Upload progress bar shown
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
├── PDF generated and downloadable
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
├── Study materials (PPTX) created
└── Optional: Mock interview chat session
10.2 Returning User Journey
text

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
11. OBSERVABILITY & MONITORING
11.1 LangSmith Integration
YAML

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
11.2 LangFuse Integration
YAML

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
11.3 Custom Real-Time Observability
YAML

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
    middleware: "Redis Pub/Sub for multi-process support"
11.4 Observability Dashboard Metrics
text

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
    ├── Database query performance
    ├── WebSocket connection count
    └── Background task queue depth
12. PROJECT STRUCTURE
text

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
│   │   ├── config.py                  # Settings & env vars
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
│   │   │   │   ├── drive_tools.py     # Google Drive tools
│   │   │   │   └── embedding_tools.py # Embedding generation
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
│   │   │   ├── quota_manager.py       # API quota tracking
│   │   │   ├── event_bus.py           # WebSocket event emitter
│   │   │   └── google_auth.py         # Google OAuth handler
│   │   │
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── database.py            # SQLAlchemy engine + session
│   │   │   ├── models.py              # ORM models
│   │   │   ├── vector_store.py        # ChromaDB setup
│   │   │   └── redis_client.py        # Redis connection
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
│   │       ├── file_handler.py        # File upload/download
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
│   ├── next.config.js
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
├── langfuse/                          # Self-hosted LangFuse (optional)
│   └── docker-compose.yml
│
├── scripts/
│   ├── setup.sh                       # Initial setup script
│   ├── seed_db.py                     # Seed database
│   └── test_agents.py                 # Test agent workflows
│
└── docs/
    ├── API.md                         # API documentation
    ├── AGENTS.md                      # Agent documentation
    ├── SETUP.md                       # Setup instructions
    └── ARCHITECTURE.md                # Architecture details
13. IMPLEMENTATION PHASES
Phase 1: Foundation (Week 1-2)
YAML

phase_1:
  name: "Foundation & Infrastructure"
  duration: "2 weeks"
  
  tasks:
    1.1_project_setup:
      - Initialize Git repository
      - Create project structure (as defined above)
      - Set up Docker Compose (PostgreSQL, Redis, ChromaDB)
      - Configure environment variables
      - Set up Python virtual environment
      - Install all backend dependencies
      - Initialize Next.js frontend with TypeScript
      - Install and configure shadcn/ui + Tailwind
    
    1.2_database_setup:
      - Set up PostgreSQL with Docker
      - Create SQLAlchemy models (all tables)
      - Configure Alembic for migrations
      - Run initial migration
      - Set up Redis connection
      - Set up ChromaDB vector store
    
    1.3_backend_api_skeleton:
      - Create FastAPI app with CORS
      - Implement JWT authentication (signup, login)
      - Create all API route files (empty handlers)
      - Set up WebSocket endpoint
      - Implement file upload endpoint
      - Create health check endpoint
    
    1.4_frontend_skeleton:
      - Create layout with sidebar navigation
      - Create all page files (empty)
      - Implement authentication pages (login/signup)
      - Set up Zustand stores
      - Configure API client
      - Set up WebSocket client hook
    
    1.5_llm_setup:
      - Configure Gemini 2.0 Flash connection
      - Configure Groq connection (Llama 3.3, Mixtral)
      - Implement LLM Router with fallback logic
      - Implement quota manager (Redis-based)
      - Test all LLM connections
      - Set up LangSmith tracing
      - Set up LangFuse (cloud or self-hosted Docker)

  deliverables:
    - Running Docker environment
    - Auth working (signup/login)
    - Empty but navigable frontend
    - All LLM connections verified
    - Database schema deployed
    - Observability tools connected
Phase 2: CV Intelligence (Week 3)
YAML

phase_2:
  name: "CV Upload, Parse & Store"
  duration: "1 week"
  
  tasks:
    2.1_cv_upload:
      - Implement file upload API (PDF, DOCX)
      - Store file on local filesystem
      - Create CV record in database
      - Frontend: CVUploader component with drag-drop
    
    2.2_cv_parser_agent:
      - Create CV Parser Agent with LangChain
      - PDF text extraction (PyPDF2 + pdfplumber)
      - DOCX text extraction (python-docx)
      - LLM-powered structured data extraction
      - Prompt engineering for CV parsing
      - Extract: personal info, summary, skills,
        experience, education, projects, certifications
      - Store parsed data as JSONB in database
    
    2.3_cv_embeddings:
      - Generate embeddings for CV sections
      - Store in ChromaDB with metadata
      - Implement semantic search capability
    
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
    - Embeddings stored in vector DB
    - Real-time parsing status visible in UI
Phase 3: Job Hunting (Week 4)
YAML

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
      - Implement semantic matching (embeddings)
      - Keyword overlap scoring
      - Experience level matching
      - Composite match score calculation
      - Identify matching and missing skills
    
    3.4_job_storage:
      - Store jobs in database
      - Store job embeddings in ChromaDB
    
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
Phase 4: CV Tailoring Engine (Week 5-6)
YAML

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
    
    4.4_comparison_ui:
      - CVComparison component (original vs tailored)
      - Side-by-side diff view
      - Changes highlighted
      - Match score before/after
      - Download tailored PDF button
    
    4.5_batch_tailoring:
      - Tailor CV for multiple jobs in batch
      - Queue management with Celery
      - Progress tracking per job
      - Batch status in dashboard
    
    4.6_observability:
      - Detailed step-by-step tracking
      - "Rewriting experience section..."
      - "Optimizing for ATS..."
      - Token usage per tailoring operation

  deliverables:
    - Select job → get 100% tailored CV + cover letter
    - Professional PDF output
    - Visual comparison of changes
    - Batch tailoring for multiple jobs
Phase 5: HR Contact & Application (Week 7)
YAML

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
      - PDF attachment handling
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
Phase 6: Interview Preparation (Week 8)
YAML

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
      - Download materials buttons

  deliverables:
    - Complete interview prep package per job
    - Mock interview chat feature
    - Downloadable study materials (PPTX, PDF)
Phase 7: LangGraph Orchestration (Week 9)
YAML

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
      - State persistence (checkpoint)
    
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
Phase 8: Dashboard & Observability (Week 10)
YAML

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
    
    8.5_langsmith_langfuse_links:
      - Deep links to LangSmith traces
      - Deep links to LangFuse analytics
      - Embedded LangFuse dashboard (iframe optional)

  deliverables:
    - Professional dashboard with real analytics
    - Full agent observability in real-time
    - Quota monitoring and warnings
Phase 9: Polish & Testing (Week 11-12)
YAML

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
    
    9.4_documentation:
      - API documentation (auto-generated by FastAPI)
      - Agent documentation
      - Setup guide
      - User guide
    
    9.5_deployment:
      - Docker Compose production config
      - Environment variable documentation
      - Health check endpoints
      - Logging configuration
      - Backup strategy

  deliverables:
    - Production-ready application
    - Full test suite
    - Complete documentation
    - Deployment ready
14. ANTIGRAVITY EXECUTION INSTRUCTIONS
14.1 Execution Order
Markdown

# ANTIGRAVITY EXECUTION PLAN
# Execute in this exact order

## STEP 1: Initialize Project
- Create the full directory structure as defined in Section 12
- Initialize git repository
- Create .env.example with all required variables
- Create docker-compose.yml with PostgreSQL, Redis, ChromaDB

## STEP 2: Backend Foundation
- Create requirements.txt with all packages from Section 5.3
- Create FastAPI main.py with CORS, middleware
- Create config.py reading all env vars
- Create database.py with SQLAlchemy async engine
- Create all ORM models from Section 6.1
- Create Alembic config and initial migration
- Create Redis client
- Create ChromaDB vector store setup
- Implement JWT auth (signup, login, token refresh)

## STEP 3: LLM Infrastructure
- Create llm_router.py with Gemini + Groq fallback
- Create quota_manager.py with Redis counters
- Configure LangSmith tracing
- Configure LangFuse callbacks
- Create event_bus.py for WebSocket events
- Test LLM connections

## STEP 4: Agents (one by one)
- Create state.py (LangGraph state schema)
- Create cv_parser.py agent + prompts
- Create job_hunter.py agent + tools + prompts
- Create cv_tailor.py agent + prompts (most complex)
- Create hr_finder.py agent + tools + prompts
- Create email_sender.py agent + Gmail tools
- Create interview_prep.py agent + prompts
- Create doc_generator.py agent + PDF/PPTX tools
- Create supervisor.py agent + routing logic
- Create graph.py (LangGraph StateGraph wiring all agents)

## STEP 5: API Routes
- Create all route handlers calling agents/services
- Create WebSocket handler for real-time updates
- Create service layer for business logic
- Create Pydantic schemas for all request/response

## STEP 6: Frontend
- Initialize Next.js 14 with TypeScript
- Install and configure shadcn/ui
- Install Tailwind CSS
- Create layout with sidebar
- Create all pages (dashboard, chat, jobs, cvs, 
  applications, interview, settings)
- Create all components as defined in Section 12
- Create Zustand stores
- Create API client and WebSocket hook
- Wire everything together

## STEP 7: Integration Testing
- Test full pipeline end-to-end
- Fix bugs and edge cases
- Performance optimization

## STEP 8: Docker & Deployment
- Create Dockerfiles for backend and frontend
- Create production docker-compose
- Final testing
14.2 Key Implementation Notes for Antigravity
Markdown

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
   - State is serializable (for Redis persistence)
   - State changes are logged

4. PROMPTS: Store all prompts in separate files
   - Use LangChain PromptTemplate
   - Include few-shot examples where needed
   - Version prompts in LangFuse

5. FREE TIER MANAGEMENT:
   - Check quota BEFORE every API call
   - Track in Redis with atomic increments
   - Show warnings in UI at 80%
   - Never crash on quota exceeded

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

9. FILE GENERATION:
   - CVs: HTML → CSS → WeasyPrint → PDF
   - Use Jinja2 templates for CV HTML
   - PPTX: python-pptx with clean templates
   - All files stored locally + optionally Google Drive

10. WEBSOCKET PROTOCOL:
    - Frontend connects on login
    - Backend pushes events per session
    - Reconnection handling
    - Event types clearly defined
14.3 Environment Setup Script
Bash

#!/bin/bash
# scripts/setup.sh

echo "🚀 Setting up Digital FTE..."

# Create directories
mkdir -p uploads generated logs

# Backend setup
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Install Playwright browsers (for web scraping)
playwright install chromium

# Download embedding model
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

cd ..

# Frontend setup
cd frontend
npm install
npx shadcn-ui@latest init
cd ..

# Start services
docker-compose up -d postgres redis chromadb

# Run migrations
cd backend
alembic upgrade head
cd ..

echo "✅ Setup complete!"
echo "📝 Don't forget to:"
echo "   1. Copy .env.example to .env"
echo "   2. Add your API keys"
echo "   3. Set up Google Cloud OAuth credentials"
14.4 Docker Compose
YAML

# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: digital_fte
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  chromadb:
    image: chromadb/chroma:latest
    ports:
      - "8000:8000"
    volumes:
      - chroma_data:/chroma/chroma
    environment:
      - IS_PERSISTENT=TRUE

  backend:
    build: ./backend
    ports:
      - "8080:8080"
    env_file:
      - .env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      chromadb:
        condition: service_started
    volumes:
      - ./uploads:/app/uploads
      - ./generated:/app/generated
    command: uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8080
      - NEXT_PUBLIC_WS_URL=ws://localhost:8080
    command: npm run dev

  # Optional: Self-hosted LangFuse
  langfuse-server:
    image: langfuse/langfuse:2
    depends_on:
      postgres:
        condition: service_healthy
    ports:
      - "3001:3000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/langfuse
      - NEXTAUTH_SECRET=mysecret
      - SALT=mysalt
      - NEXTAUTH_URL=http://localhost:3001
      - TELEMETRY_ENABLED=${TELEMETRY_ENABLED:-true}
      - LANGFUSE_ENABLE_EXPERIMENTAL_FEATURES=${LANGFUSE_ENABLE_EXPERIMENTAL_FEATURES:-false}

  celery-worker:
    build: ./backend
    env_file:
      - .env
    depends_on:
      - redis
      - postgres
    command: celery -A app.celery_app worker --loglevel=info --concurrency=4

volumes:
  postgres_data:
  redis_data:
  chroma_data:
SUMMARY
text

┌────────────────────────────────────────────────────────┐
│              DIGITAL FTE - PROJECT SUMMARY              │
├────────────────────────────────────────────────────────┤
│                                                        │
│  🏗️  Architecture: Multi-Agent AI System               │
│  🤖  Agents: 8 specialized + 1 supervisor              │
│  🧠  LLMs: Gemini Flash + Groq (free tier)             │
│  🔗  Orchestration: LangGraph + LangChain              │
│  📊  Observability: LangSmith + LangFuse               │
│  🖥️  Frontend: Next.js 14 + shadcn/ui                  │
│  ⚙️  Backend: FastAPI + Python 3.12                     │
│  🗄️  Database: PostgreSQL + Redis + ChromaDB            │
│  📁  Files: WeasyPrint (PDF) + python-pptx              │
│  📧  Email: Gmail API                                   │
│  🔍  Jobs: SerpAPI + RapidAPI JSearch                   │
│  👤  HR: Hunter.io + Apollo.io                          │
│  🐳  Deploy: Docker Compose                             │
│  📅  Timeline: 12 weeks                                 │
│  💰  Cost: $0 (all free tier APIs)                      │
│                                                        │
│  FLOW: Upload CV → Find Jobs → Tailor CV →             │
│        Find HR → Send Email → Prep Interview           │
│                                                        │
│  ALL with full observability, real-time tracking,       │
│  human approval gates, and expandable architecture.    │
│                                                        │
└────────────────────────────────────────────────────────┘