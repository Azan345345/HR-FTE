# Digital FTE — AI-Powered Job Application Automation Agent

<div align="center">

![Digital FTE Banner](https://img.shields.io/badge/Digital%20FTE-AI%20Job%20Agent-6366F1?style=for-the-badge&logo=robot&logoColor=white)

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.3-61DAFB?style=flat-square&logo=react)](https://reactjs.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2.60+-FF6B35?style=flat-square)](https://langchain-ai.github.io/langgraph/)
[![Gemini](https://img.shields.io/badge/Gemini-2.5%20Flash-4285F4?style=flat-square&logo=google)](https://deepmind.google/technologies/gemini/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.8-3178C6?style=flat-square&logo=typescript)](https://www.typescriptlang.org/)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

**Digital FTE is a fully autonomous, multi-agent AI system that handles your entire job application pipeline — from CV parsing and tailoring, to finding HR contacts, composing personalised emails, and sending them with your PDF CV attached — all with human-in-the-loop approval.**

[Features](#-features) • [Architecture](#-architecture) • [Quick Start](#-quick-start) • [API Reference](#-api-reference) • [Configuration](#-configuration) • [Agents](#-agents) • [Database](#-database-schema) • [Frontend](#-frontend) • [Contributing](#-contributing)

</div>

---

## Table of Contents

1. [Overview](#-overview)
2. [Features](#-features)
3. [System Architecture](#-system-architecture)
4. [Tech Stack](#-tech-stack)
5. [Project Structure](#-project-structure)
6. [Agent Pipeline Flow](#-agent-pipeline-flow)
7. [LangGraph State Machine](#-langgraph-state-machine)
8. [Agent Details](#-agent-details)
   - [CV Parser](#1-cv-parser)
   - [Job Hunter](#2-job-hunter)
   - [CV Tailor](#3-cv-tailor)
   - [HR Finder](#4-hr-finder)
   - [Email Composer](#5-email-composer)
   - [Document Generator](#6-document-generator)
   - [Email Sender](#7-email-sender)
   - [Interview Prep](#8-interview-prep)
   - [Supervisor](#9-supervisor)
   - [Gmail Watcher](#10-gmail-watcher)
9. [Database Schema](#-database-schema)
10. [API Reference](#-api-reference)
11. [Frontend Architecture](#-frontend-architecture)
12. [WebSocket Protocol](#-websocket-protocol)
13. [LLM Router & Fallback Chain](#-llm-router--fallback-chain)
14. [Skills System](#-skills-system)
15. [Human-in-the-Loop (HITL)](#-human-in-the-loop-hitl)
16. [Observability & Monitoring](#-observability--monitoring)
17. [Configuration Reference](#-configuration-reference)
18. [Quick Start](#-quick-start)
19. [Environment Setup](#-environment-setup)
20. [Running in Production](#-running-in-production)
21. [Contributing](#-contributing)

---

## Overview

**Digital FTE** (Full-Time Employee) is your personal AI career agent. It automates the most time-consuming and repetitive parts of job hunting:

- **Parses** your CV (PDF or DOCX) into a rich structured JSON
- **Finds** jobs matching your skills via SerpAPI / RapidAPI
- **Tailors** your CV and writes a cover letter for each specific job
- **Locates** the HR manager's direct email using Hunter.io, Prospeo, Apify, and Snov.io
- **Composes** a professional AIDA-framework application email
- **Waits** for your approval in a chat interface before sending
- **Generates** a professional PDF of your tailored CV using ReportLab
- **Sends** the email with your PDF CV attached via Gmail API
- **Prepares** you for interviews with company research, Q&A, and salary data
- **Watches** your Gmail inbox for recruiter replies

The system is built around a **LangGraph state machine** with 11 nodes, a **FastAPI** backend, a **React + TypeScript** frontend, and **Google Gemini 2.5 Flash** as the primary LLM with a full fallback chain to Groq models.

---

## Features

### Core Automation
- **Autonomous Multi-Job Pipeline** — Queue multiple jobs, process them one by one without manual intervention
- **CV Parsing** — Extracts personal info, skills, experience, education, projects from PDF/DOCX
- **Intelligent Job Search** — Searches across multiple sources, scores jobs against your CV
- **CV Tailoring** — Rewrites bullet points, adds JD-matched experience, removes irrelevant skills, adjusts keywords for ATS
- **ATS Optimization** — Calculates ATS score and match score for each tailored CV
- **HR Contact Discovery** — Finds direct recruiter emails using 4 APIs + LLM fallback
- **Email Composition** — Writes AIDA-structured personalised application emails
- **PDF Generation** — Creates professional A4-format CV PDFs with ReportLab
- **Gmail Integration** — Sends emails via Gmail API with PDF attachment
- **Interview Preparation** — Generates technical, behavioral, situational, and cultural Q&A + salary research

### Human-in-the-Loop
- **Chat-First Approval Flow** — All emails and CVs require explicit user approval before sending
- **Rich Action Cards** — Interactive UI cards for approving CVs, emails, and triggering actions
- **Live Editing** — Edit email body, subject, or cover letter in real-time via chat
- **Regeneration** — Regenerate any document with one click

### Real-Time
- **WebSocket-Powered** — Live agent progress updates, logs, and approval requests via WebSocket
- **Event Bus** — Internal asyncio pub/sub for decoupled agent communication
- **Gmail Inbox Watcher** — Background polling for recruiter replies

### Observability
- **LangSmith Integration** — Full LangChain trace logging
- **Langfuse Integration** — Prompt analytics and performance tracking
- **Agent Execution Logs** — Every agent action logged to DB with token counts, timing, and errors
- **API Quota Dashboard** — Per-provider daily/monthly quota tracking

### Security
- **JWT Authentication** — HS256, 24-hour access tokens
- **bcrypt Password Hashing** — Industry-standard password security
- **Google OAuth 2.0** — Single sign-on with Google
- **Per-User Data Isolation** — All data scoped by `user_id` with foreign key cascades

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React)                         │
│  LeftSidebar │ CenterPanel (Chat) │ RightSidebar │ TopBar       │
│  JobsView │ ApplicationTracker │ InterviewPrepView │ Settings    │
└───────────────────────┬─────────────────────────────────────────┘
                        │  REST + WebSocket
┌───────────────────────▼─────────────────────────────────────────┐
│                      FASTAPI BACKEND                            │
│                                                                 │
│  /api/auth  /api/chat  /api/cv  /api/jobs  /api/applications   │
│  /api/dashboard  /api/interview  /api/integrations             │
│  /api/observability  /api/settings  /ws (WebSocket)            │
└───────────────────────┬─────────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────────┐
│                    LANGGRAPH STATE MACHINE                       │
│                                                                 │
│  START → supervisor ──────────────────────────────────────┐    │
│              │                                            │    │
│     ┌────────▼────────┐                                   │    │
│     │   cv_parser     │                                   │    │
│     │   job_hunter    │                                   │    │
│     │   cv_tailor     │◄──────── automation_queue         │    │
│     │   hr_finder     │                                   │    │
│     │   email_drafter │                                   │    │
│     │   human_approval│── user approves ──► pdf_generator │    │
│     │   editor_node   │                         │         │    │
│     │   email_sender  │◄────────────────────────┘         │    │
│     │   interview_prep│                                   │    │
│     └─────────────────┘                                   │    │
│              └──────────────── more jobs? ────────────────┘    │
└───────────────────────┬─────────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
   ┌─────────┐   ┌──────────┐   ┌──────────────┐
   │ SQLite  │   │  Upstash │   │  External    │
   │ (dev)   │   │  Redis   │   │  APIs        │
   │ Supa-   │   │  Cache   │   │  (Gemini,    │
   │ base    │   │          │   │   Groq, etc) │
   │ (prod)  │   └──────────┘   └──────────────┘
   └─────────┘
```

---

## Tech Stack

### Backend
| Technology | Version | Purpose |
|------------|---------|---------|
| **FastAPI** | 0.115+ | REST API framework |
| **SQLAlchemy** | 2.0+ | Async ORM |
| **SQLite** | — | Development database |
| **Supabase PostgreSQL** | — | Production database |
| **Alembic** | 1.14+ | Database migrations |
| **LangGraph** | 0.2.60+ | Multi-agent state machine |
| **LangChain** | 0.3+ | LLM abstraction layer |
| **structlog** | 24.4+ | Structured logging |
| **Uvicorn** | 0.34+ | ASGI server |
| **python-jose** | 3.3+ | JWT tokens |
| **passlib[bcrypt]** | 1.7+ | Password hashing |
| **ReportLab** | 4.4+ | PDF generation |
| **python-pptx** | 1.0+ | PPTX generation |
| **pdfplumber / pypdf** | — | PDF parsing |
| **python-docx** | 1.1+ | DOCX parsing |
| **sentence-transformers** | 3.3+ | Local embeddings |
| **pgvector** | 0.3+ | Vector similarity search |
| **upstash-redis** | 1.1+ | Caching layer |
| **google-api-python-client** | 2.159+ | Gmail API |
| **httpx / requests** | — | HTTP clients |
| **tenacity** | 9.0+ | Retry logic |

### AI / LLM
| Provider | Model | Role |
|----------|-------|------|
| **Google Gemini** | gemini-2.5-flash | Primary LLM |
| **Groq** | gpt-oss-120b | Secondary LLM |
| **Groq** | llama-3.3-70b-versatile | Fallback 1 |
| **Groq** | mixtral-8x7b-32768 | Fallback 2 |
| **Groq** | llama-3.1-8b-instant | Fallback 3 |
| **LangSmith** | — | Trace logging |
| **Langfuse** | — | Prompt analytics |

### External APIs
| API | Purpose | Free Tier |
|-----|---------|-----------|
| **SerpAPI** | Google Jobs search | 100 searches/month |
| **RapidAPI** | Job board aggregation | Varies |
| **Hunter.io** | HR email finding | 25 searches/month |
| **Prospeo** | HR email finding | 150 searches/month |
| **Apify** | LinkedIn scraping | Free tier |
| **Snov.io** | HR email finding | 50 searches/month |
| **Gmail API** | Email sending/watching | Free |

### Frontend
| Technology | Version | Purpose |
|------------|---------|---------|
| **React** | 18.3 | UI framework |
| **TypeScript** | 5.8 | Type safety |
| **Vite** | 5.4 | Build tool |
| **Zustand** | 5.0 | State management |
| **TanStack Query** | 5.x | Server state / caching |
| **shadcn/ui** | — | Component library |
| **Radix UI** | — | Accessible primitives |
| **Tailwind CSS** | 3.4 | Utility CSS |
| **Framer Motion** | 12.x | Animations |
| **React Router** | 6.x | Client-side routing |
| **react-markdown** | 10.x | Markdown rendering |
| **recharts** | 2.x | Charting |
| **lucide-react** | 0.462 | Icons |

---

## Project Structure

```
FTE HR/
├── backend/
│   ├── app/
│   │   ├── agents/                  # All AI agents
│   │   │   ├── state.py             # DigitalFTEState TypedDict
│   │   │   ├── graph.py             # LangGraph 11-node state machine
│   │   │   ├── supervisor.py        # Chat intent router + graph invoker
│   │   │   ├── cv_parser.py         # PDF/DOCX parsing agent
│   │   │   ├── cv_tailor.py         # CV tailoring + ATS scoring agent
│   │   │   ├── job_hunter.py        # Job search agent
│   │   │   ├── hr_finder.py         # HR contact discovery agent
│   │   │   ├── email_sender.py      # Email composition + Gmail sending
│   │   │   ├── doc_generator.py     # ReportLab PDF + PPTX generation
│   │   │   ├── interview_prep.py    # Interview Q&A + company research
│   │   │   └── gmail_watcher.py     # Background Gmail inbox poller
│   │   │
│   │   ├── api/
│   │   │   ├── router.py            # Central API router
│   │   │   ├── deps.py              # FastAPI dependencies (auth, DB)
│   │   │   ├── routes/
│   │   │   │   ├── auth.py          # Register, login, Google OAuth
│   │   │   │   ├── chat.py          # Chat + file context upload
│   │   │   │   ├── cv.py            # CV upload, parse, list, delete
│   │   │   │   ├── jobs.py          # Job search, list, score
│   │   │   │   ├── applications.py  # Application CRUD + status
│   │   │   │   ├── dashboard.py     # Stats + recent activity
│   │   │   │   ├── interview.py     # Interview prep CRUD
│   │   │   │   ├── integrations.py  # Google OAuth token management
│   │   │   │   ├── observability.py # Agent logs + quota usage
│   │   │   │   └── settings.py      # User preferences
│   │   │   └── websocket/
│   │   │       └── handler.py       # WebSocket auth + event relay
│   │   │
│   │   ├── core/
│   │   │   ├── llm_router.py        # LLM selection + fallback chain
│   │   │   ├── security.py          # JWT creation/verification
│   │   │   ├── google_auth.py       # Google OAuth flow
│   │   │   ├── quota_manager.py     # Per-provider rate limit tracking
│   │   │   ├── event_bus.py         # asyncio pub/sub EventBus
│   │   │   ├── skills.py            # Skills file loader
│   │   │   └── redis_client.py      # Upstash Redis wrapper
│   │   │
│   │   ├── db/
│   │   │   ├── database.py          # Async SQLAlchemy engine + session
│   │   │   └── models.py            # 14 ORM models
│   │   │
│   │   ├── orchestration/
│   │   │   └── pipeline_controller.py  # Autonomous multi-job pipeline
│   │   │
│   │   ├── schemas/
│   │   │   └── schemas.py           # All Pydantic request/response models
│   │   │
│   │   ├── config.py                # Pydantic Settings (env vars)
│   │   └── main.py                  # FastAPI app entry + CORS + WebSocket
│   │
│   ├── uploads/                     # Uploaded CV files
│   ├── generated/                   # Generated PDFs + PPTX files
│   ├── requirements.txt
│   └── venv/                        # Python virtual environment
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── TopBar.tsx           # Top navigation bar
│   │   │   ├── LeftSidebar.tsx      # Navigation + data sources panel
│   │   │   ├── CenterPanel.tsx      # Chat interface + message bubbles
│   │   │   ├── RightSidebar.tsx     # Agent activity + draft previews
│   │   │   ├── JobsView.tsx         # Job search results + chat
│   │   │   ├── ApplicationTracker.tsx  # Application pipeline tracker
│   │   │   ├── InterviewPrepView.tsx   # Interview Q&A display
│   │   │   ├── ObservabilityView.tsx   # Agent logs + quota charts
│   │   │   ├── SeeingInView.tsx     # Parsed CV + data viewer
│   │   │   ├── SettingsModal.tsx    # User settings + integrations
│   │   │   ├── CommandPalette.tsx   # Keyboard command palette
│   │   │   ├── NotificationPanel.tsx   # Real-time notifications
│   │   │   ├── FileUploadModal.tsx  # CV upload dialog
│   │   │   ├── WelcomeScreen.tsx    # Onboarding screen
│   │   │   ├── HitLBlock.tsx        # Human-in-the-loop approval block
│   │   │   └── chat-cards/          # Rich action card components
│   │   │       ├── TailorCard.tsx
│   │   │       ├── CVApprovalCard.tsx
│   │   │       ├── EmailApprovalCard.tsx
│   │   │       ├── RegenerateCard.tsx
│   │   │       └── InterviewCard.tsx
│   │   │
│   │   ├── stores/
│   │   │   └── agent-store.ts       # Zustand global state
│   │   │
│   │   ├── lib/
│   │   │   ├── api.ts               # Typed fetch wrapper + JWT injection
│   │   │   └── utils.ts             # Tailwind cn() helper
│   │   │
│   │   ├── hooks/                   # Custom React hooks
│   │   ├── pages/                   # Route-level page components
│   │   └── services/                # Service layer (WebSocket, etc.)
│   │
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   └── tsconfig.json
│
├── skills/                          # AI skill prompt files
│   ├── 01-email-writing/
│   ├── 02-cover-letter-writting/
│   ├── 03-cv-resume-writing/
│   ├── 04-regional-adaptation/
│   ├── 05-ats-optimization/
│   └── _shared/
│
├── .env.example                     # Environment variable template
├── DIGITAL_FTE_PLAN.md              # Original project plan
└── README.md                        # This file
```

---

## Agent Pipeline Flow

The system follows a deterministic pipeline that can run autonomously or pause for human review at any stage:

```
┌──────────────┐
│  User Chat   │  "Find me software engineer jobs in London"
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Supervisor  │  Classifies intent, routes to correct agent
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  CV Parser   │  Parses uploaded CV → structured JSON + embeddings
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Job Hunter  │  Searches SerpAPI/RapidAPI → scored job list (saved to DB)
└──────┬───────┘
       │
       ▼ (for each job in queue)
┌──────────────┐
│  CV Tailor   │  Rewrites CV for job → tailored_cv + cover_letter + ATS score
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  HR Finder   │  Hunter.io / Prospeo / Apify → HR contact email
└──────┬───────┘
       │
       ▼
┌──────────────┐
│Email Composer│  AIDA-framework email → subject + body
└──────┬───────┘
       │
       ▼
┌──────────────┐
│Human Approval│  ← USER REVIEWS in chat UI ←─────────┐
│    (HITL)    │                                        │
└──────┬───────┘                                        │
       │ Approved?                          No → Editor Node
       ▼                                   (rewrite based on feedback)
┌──────────────┐
│PDF Generator │  ReportLab → tailored CV as A4 PDF
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Email Sender │  Gmail API → send email with PDF attachment
└──────┬───────┘
       │
       ▼ (next job in queue? → back to CV Tailor)
┌──────────────┐
│ Gmail Watcher│  Background: poll inbox for recruiter replies
└──────────────┘
       │
       ▼ (separately, on demand)
┌──────────────┐
│Interview Prep│  Company research + Q&A + salary → PPTX study slides
└──────────────┘
```

---

## LangGraph State Machine

The entire workflow is encoded as a **LangGraph `StateGraph`** operating on a shared `DigitalFTEState` TypedDict. Each node is an async function that reads from and writes to the state.

### State Schema (`DigitalFTEState`)

```python
class DigitalFTEState(TypedDict, total=False):
    # User context
    user_id: str
    session_id: str
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
    tailored_cvs: List[dict]

    # HR Contacts
    hr_contacts: List[dict]

    # Applications
    applications_sent: List[dict]
    pending_approvals: List[dict]

    # Automation Queue
    automation_queue: List[dict]      # Jobs waiting to be processed
    current_work_item: Optional[dict] # Job currently being processed

    # Human-in-the-loop
    user_approvals: dict              # {job_id: {cv: bool, email: bool}}
    draft_cv: Optional[dict]
    draft_email: Optional[dict]
    draft_cover_letter: Optional[str]
    tailored_cv_pdf_path: Optional[str]
    waiting_for_user: bool

    # Interview Prep
    interview_prep_data: List[dict]

    # Agent Orchestration
    current_agent: str
    agent_plan: str
    agent_status: str
    execution_log: List[dict]
    errors: List[str]

    # Control Flow
    next_step: str
    full_pipeline_requested: bool
    requires_user_input: bool
    user_approval_needed: bool
    response_text: str
```

### Graph Nodes

| Node | Trigger | Action |
|------|---------|--------|
| `supervisor` | START, all agent completions | Classify intent, decide next node |
| `cv_parser` | Missing parsed CV | Parse uploaded CV file |
| `job_hunter` | Job search request | Search APIs, score against CV |
| `cv_tailor` | Job in queue | Tailor CV, write cover letter |
| `hr_finder` | CV tailored | Find HR contact email |
| `email_drafter` | HR found | Compose application email |
| `human_approval` | Email drafted | Pause, show user for review |
| `editor_node` | User feedback | Apply edits to email/CV/cover letter |
| `pdf_generator` | User approved | Generate PDF of tailored CV |
| `email_sender` | PDF ready | Send email via Gmail API |
| `interview_prep` | On demand | Generate interview Q&A |

### Routing Logic

```
supervisor → conditional route based on next_step:
  "parse_cv"       → cv_parser
  "find_jobs"      → job_hunter
  "tailor_cv"      → cv_tailor
  "find_hr"        → hr_finder
  "draft_email"    → email_drafter
  "human_approval" → human_approval
  "generate_pdf"   → pdf_generator
  "send_email"     → email_sender
  "prep_interview" → interview_prep
  "editor_node"    → editor_node
  "end"            → END

human_approval → user approved? → supervisor (→ pdf_generator)
              → not approved?  → END (pause turn, wait for chat)

editor_node → supervisor (re-trigger human_approval)

email_sender → more jobs in queue? → supervisor
            → queue empty?        → END

pdf_generator → supervisor (→ send_email)
```

---

## Agent Details

### 1. CV Parser

**File:** `backend/app/agents/cv_parser.py`

Extracts structured data from uploaded CV files (PDF or DOCX).

**Capabilities:**
- Supports PDF (via `pdfplumber` + `pypdf`) and DOCX (via `python-docx`)
- Sends raw text to Gemini with a structured extraction prompt
- Returns a rich JSON object with:
  - `personal_info`: name, email, phone, location, LinkedIn, GitHub, portfolio, date of birth, nationality, gender, marital status, visa status
  - `summary`: professional summary
  - `skills`: categorised dict (e.g., `{"languages": [...], "frameworks": [...]}`)
  - `experience`: list of roles with company, duration, achievements
  - `education`: degrees, institutions, years
  - `projects`: name, description, technologies
  - `certifications`: list
  - `languages`: spoken languages
- Generates sentence-transformer embeddings per CV section (stored in `cv_embeddings` table)

**Output fields stored in DB:**
- `UserCV.parsed_data` — the full JSON
- `UserCV.raw_text` — the raw extracted text
- `CVEmbedding` rows — one per section for vector search

---

### 2. Job Hunter

**File:** `backend/app/agents/job_hunter.py`

Searches job boards and scores results against the candidate's CV.

**Search Sources:**
- **SerpAPI** — Google Jobs API (primary)
- **RapidAPI** — LinkedIn Jobs / JSearch aggregator (fallback)

**Scoring Algorithm:**
- Extracts skills from job description via LLM
- Computes skill overlap with CV skills
- Scores 0–100 based on: skill match %, required keywords present, location match, experience level alignment
- Tags each job with `matching_skills` and `missing_skills`

**DB Output:**
- Creates a `JobSearch` record (query, filters, status)
- Creates one `Job` record per result with full metadata
- Returns jobs sorted by `match_score` descending

**State Output:**
```python
{
    "jobs_found": [...],          # Full job list
    "automation_queue": [...],    # Same list, consumed by supervisor
    "response_text": "Found 5 jobs..."
}
```

---

### 3. CV Tailor

**File:** `backend/app/agents/cv_tailor.py`

Tailors the user's parsed CV for a specific job description using LLM.

**What it does:**
- Sends the full parsed CV JSON + job description to Gemini
- Uses the skills files from `skills/03-cv-resume-writing/` and `skills/05-ats-optimization/` to guide the prompt
- Returns a complete rewritten CV as JSON with:
  - `tailored_cv`: full CV JSON with updated summary, rewritten achievements, added keywords
  - `cover_letter`: full personalised cover letter text
  - `ats_score`: 0–100 ATS compatibility score
  - `match_score`: 0–100 semantic match to job description
  - `changes_made`: list of changes for audit trail
  - `skills_to_remove`: list of irrelevant skills to exclude from PDF
  - `non_cv_sections.work_experience`: new experience entries synthesised from JD requirements

**Key behaviour:**
- `skills_to_remove` entries are deleted from the tailored CV before saving
- `non_cv_sections.work_experience` entries are merged into existing experience
- The `_apply_improvements()` function handles both operations safely

**DB Output:**
- Creates a `TailoredCV` record with `tailored_data`, `cover_letter`, `ats_score`, `match_score`

---

### 4. HR Finder

**File:** `backend/app/agents/hr_finder.py`

Finds the direct email address of the hiring manager or HR contact at the target company.

**Discovery Chain (tries in order):**
1. **Hunter.io** — `GET /domain-search?domain=<company>.com&department=hr`
2. **Prospeo** — Domain email finder API
3. **Apify** — LinkedIn people search actor for `{company} HR Manager`
4. **Snov.io** — Email finder by domain + job title
5. **LLM Fallback** — Generates a best-guess email based on company naming patterns (e.g., `firstname.lastname@company.com`)

**Output:**
```python
{
    "name": "Jane Smith",
    "email": "j.smith@company.com",
    "title": "HR Manager",
    "linkedin": "linkedin.com/in/jsmith",
    "confidence_score": 0.85,
    "source": "hunter.io",
    "verified": True
}
```

**DB Output:**
- Creates an `HRContact` record linked to the job

---

### 5. Email Composer

**File:** `backend/app/agents/email_sender.py` (compose function)

Composes a personalised job application email using the **AIDA framework** (Attention, Interest, Desire, Action).

**Input:**
- Job details (title, company, description)
- Parsed CV (candidate name, key skills, experience)
- HR contact (name for personalisation)
- Cover letter (referenced in body)

**Output:**
```python
{
    "email_subject": "Application for Senior Software Engineer — Jane Smith",
    "email_body": "Dear Jane,\n\nI noticed your posting for...",
    "to_email": "j.smith@company.com"
}
```

**Prompt guidance:** Uses `skills/01-email-writing/` and `skills/02-cover-letter-writting/` files.

---

### 6. Document Generator

**File:** `backend/app/agents/doc_generator.py`

Generates professional PDF and PPTX documents.

#### PDF Generation (`generate_cv_pdf_bytes`)
- Built with **ReportLab** (version 4.4.10+)
- A4 page size with 0.75" margins
- Custom styles: Indigo (`#6366F1`) headings, clean body text
- Sections rendered: Name, Contact, Summary, Skills, Experience (with bullet achievements), Education, Projects
- Text encoding: latin-1 with `errors="replace"` for safe special character handling
- Hard fallback: minimal canvas PDF if full generation fails (never returns `None`)

#### PPTX Generation (`generate_interview_pptx`)
- Built with **python-pptx**
- 13.333" × 7.5" widescreen slides
- Title slide + Company Research slide + Technical Q&A slides (up to 5)
- Saved to `backend/generated/prep_<uuid>.pptx`

---

### 7. Email Sender

**File:** `backend/app/agents/email_sender.py` (send function)

Sends the application email via **Gmail API** with the tailored CV PDF attached.

**Process:**
1. Loads OAuth tokens from DB (`UserIntegration` table)
2. Builds MIME multipart message:
   - `text/plain` body
   - `application/pdf` attachment (the generated PDF bytes)
3. Calls Gmail API `users.messages.send`
4. Stores `gmail_message_id` in the `Application` record

**Required:** User must have completed Google OAuth flow in Settings.

---

### 8. Interview Prep

**File:** `backend/app/agents/interview_prep.py`

Generates a comprehensive interview preparation package for a given job.

**Output sections:**
- **Company Research**: overview, culture, recent news, products, tech stack
- **Technical Questions**: 10+ role-specific questions with model answers
- **Behavioral Questions**: STAR-method questions with example answers
- **Situational Questions**: scenario-based questions
- **Cultural Fit Questions**: values-alignment questions
- **System Design Questions**: (for engineering roles)
- **Coding Challenges**: (for technical roles)
- **Salary Research**: market rates, negotiation tips, range for the role/location
- **Questions to Ask**: smart questions to ask the interviewer
- **Study Plan**: structured day-by-day prep schedule
- **Tips**: role-specific interview tips

**DB Output:**
- Creates an `InterviewPrep` record with all sections stored as JSON columns

---

### 9. Supervisor

**File:** `backend/app/agents/supervisor.py`

The entry point for all chat messages. Routes user intent to the correct LangGraph flow.

**Intent Classification:**
- Detects CV upload intent → triggers `cv_parser`
- Detects job search intent → triggers `job_hunter`
- Detects interview prep intent → triggers `interview_prep`
- Detects approval intent ("yes", "approve", "send") → triggers `pdf_generator`
- Detects edit intent → triggers `editor_node`
- General queries → responds via LLM directly

**Action Prefix Routing:**
The supervisor also handles special action prefixes from the frontend:
```
__TAILOR_APPLY__:{job_search_id}:{job_id}   → tailor CV for specific job
__APPROVE_CV__:{tc_id}                       → approve tailored CV
__SEND_EMAIL__:{tc_id}                       → trigger email send
__REGENERATE_CV__:{tc_id}                    → regenerate tailored CV
__PREP_INTERVIEW__:{job_id}                  → start interview prep
```

**Response format:** Returns `Tuple[str, Optional[dict]]` — the text response plus optional metadata for rich UI card rendering.

---

### 10. Gmail Watcher

**File:** `backend/app/agents/gmail_watcher.py`

A background asyncio task that polls the user's Gmail inbox for recruiter replies.

**Behaviour:**
- Starts on app startup (in `main.py` lifespan)
- Polls every 5 minutes
- Looks for replies to sent application emails (matched by `gmail_message_id`)
- When a reply is detected, updates the `Application` status and emits a WebSocket `notification` event
- Gracefully stops on app shutdown

---

## Database Schema

The system uses **14 SQLAlchemy ORM models** stored in SQLite (dev) or Supabase PostgreSQL (prod).

### Entity Relationship Overview

```
User ─────────────── UserCV ─── CVEmbedding
  │                    │
  │               (is_primary)
  │
  ├── JobSearch ─── Job ─── JobEmbedding
  │                  │
  │                  ├── TailoredCV
  │                  ├── HRContact
  │                  ├── Application ─── InterviewPrep
  │                  └── InterviewPrep
  │
  ├── Application
  ├── UserIntegration
  └── ChatMessage
      AgentExecution (audit log)
      APIQuotaUsage (per provider/day)
```

### Tables

#### `users`
| Column | Type | Notes |
|--------|------|-------|
| id | String (UUID) | Primary key |
| email | String(255) | Unique, indexed |
| name | String(255) | Display name |
| password_hash | String(255) | bcrypt hash |
| google_oauth_token | JSON | OAuth access token |
| google_refresh_token | Text | OAuth refresh token |
| preferences | JSON | User settings dict |
| created_at | DateTime | UTC |
| updated_at | DateTime | Auto-updated |

#### `user_cvs`
| Column | Type | Notes |
|--------|------|-------|
| id | String (UUID) | Primary key |
| user_id | FK → users | CASCADE delete |
| file_name | String(255) | Original filename |
| file_path | Text | Server path |
| file_type | String(10) | "pdf" or "docx" |
| parsed_data | JSON | Full structured CV |
| raw_text | Text | Extracted plain text |
| is_primary | Boolean | Active CV flag |

#### `cv_embeddings`
| Column | Type | Notes |
|--------|------|-------|
| id | String (UUID) | Primary key |
| user_id | FK → users | CASCADE |
| cv_id | FK → user_cvs | CASCADE |
| section | String(50) | "skills", "experience", etc. |
| content | Text | Section text |
| metadata_ | JSON | Extra metadata |

#### `job_searches`
| Column | Type | Notes |
|--------|------|-------|
| id | String (UUID) | Primary key |
| user_id | FK → users | CASCADE |
| cv_id | FK → user_cvs | Optional |
| search_query | Text | Raw search query |
| target_role | String(255) | Extracted role |
| target_location | String(255) | Extracted location |
| filters | JSON | Additional filters |
| status | String(50) | pending / complete |

#### `jobs`
| Column | Type | Notes |
|--------|------|-------|
| id | String (UUID) | Primary key |
| search_id | FK → job_searches | CASCADE |
| title | String(255) | Job title |
| company | String(255) | Company name |
| location | String(255) | Job location |
| salary_range | String(100) | e.g. "£50k-£70k" |
| job_type | String(50) | full-time / contract |
| description | Text | Full JD |
| requirements | JSON | List of requirements |
| match_score | Float | 0–100 CV match |
| matching_skills | JSON | Skills in common |
| missing_skills | JSON | Skills to develop |
| source | String(50) | "serpapi" / "rapidapi" |

#### `tailored_cvs`
| Column | Type | Notes |
|--------|------|-------|
| id | String (UUID) | Primary key |
| user_id | FK → users | CASCADE |
| job_id | FK → jobs | CASCADE |
| tailored_data | JSON | Full tailored CV JSON |
| pdf_path | Text | Path to generated PDF |
| cover_letter | Text | Full cover letter |
| ats_score | Float | ATS compatibility |
| match_score | Float | Semantic match score |
| changes_made | JSON | Audit of changes |
| version | Integer | Incremented on regen |
| status | String(50) | draft / approved / sent |

#### `hr_contacts`
| Column | Type | Notes |
|--------|------|-------|
| id | String (UUID) | Primary key |
| job_id | FK → jobs | CASCADE |
| hr_name | String(255) | Full name |
| hr_email | String(255) | Email address |
| hr_title | String(255) | Job title |
| confidence_score | Float | 0.0–1.0 confidence |
| source | String(100) | "hunter.io" / "prospeo" / etc. |
| verified | Boolean | Email verified flag |

#### `applications`
| Column | Type | Notes |
|--------|------|-------|
| id | String (UUID) | Primary key |
| user_id | FK → users | CASCADE |
| job_id | FK → jobs | CASCADE |
| tailored_cv_id | FK → tailored_cvs | Optional |
| hr_contact_id | FK → hr_contacts | Optional |
| email_subject | Text | Sent email subject |
| email_body | Text | Sent email body |
| email_sent_at | DateTime | When sent |
| gmail_message_id | String(255) | For reply tracking |
| status | String(50) | pending_approval / sent / replied |
| user_approved | Boolean | HITL approval flag |
| follow_up_count | Integer | Auto follow-up count |

#### `interview_preps`
| Column | Type | Notes |
|--------|------|-------|
| id | String (UUID) | Primary key |
| user_id | FK → users | CASCADE |
| job_id | FK → jobs | CASCADE |
| company_research | JSON | Company overview dict |
| technical_questions | JSON | List of Q&A dicts |
| behavioral_questions | JSON | STAR Q&A list |
| situational_questions | JSON | Scenario Q&A list |
| cultural_questions | JSON | Values-fit Q&A |
| system_design_questions | JSON | Architecture Q&A |
| coding_challenges | JSON | Coding problem list |
| salary_research | JSON | Market rate data |
| questions_to_ask | JSON | Smart questions list |
| study_plan | JSON | Day-by-day schedule |
| prep_score | Float | Readiness score |

#### `agent_executions`
| Column | Type | Notes |
|--------|------|-------|
| id | String (UUID) | Primary key |
| session_id | String | Indexed |
| agent_name | String(100) | Which agent ran |
| action | String(255) | What it did |
| input_data | JSON | Input state snapshot |
| output_data | JSON | Output state snapshot |
| llm_model | String(100) | Which LLM was used |
| tokens_input | Integer | Input token count |
| tokens_output | Integer | Output token count |
| execution_time_ms | Integer | Duration |
| status | String(50) | success / error |
| trace_id | String(255) | LangSmith trace ID |
| langfuse_trace_id | String(255) | Langfuse trace ID |

#### `api_quota_usage`
| Column | Type | Notes |
|--------|------|-------|
| provider | String(100) | "google", "groq", etc. |
| model | String(100) | Model ID |
| date | Date | UTC date |
| requests_used | Integer | Daily request count |
| tokens_used | Integer | Daily token count |
| requests_limit | Integer | Daily limit |
| tokens_limit | Integer | Daily token limit |

#### `chat_messages`
| Column | Type | Notes |
|--------|------|-------|
| id | String (UUID) | Primary key |
| user_id | FK → users | CASCADE |
| session_id | String | Conversation thread |
| role | String(20) | "user" / "assistant" |
| agent_name | String(100) | Which agent responded |
| content | Text | Message text |
| metadata_ | JSON | Rich card metadata |

#### `user_integrations`
| Column | Type | Notes |
|--------|------|-------|
| user_id | FK → users | CASCADE |
| service_name | String(100) | "gmail", "google_oauth" |
| access_token | Text | Encrypted token |
| refresh_token | Text | For token refresh |
| token_expiry | DateTime | When to refresh |
| scopes | JSON | Granted OAuth scopes |
| is_active | Boolean | Integration enabled |

---

## API Reference

Base URL: `http://localhost:8000`

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Create account |
| POST | `/api/auth/login` | Get JWT token |
| GET | `/api/auth/me` | Get current user |
| POST | `/api/auth/google` | Google OAuth login |
| POST | `/api/auth/refresh` | Refresh JWT |

**Login Request:**
```json
POST /api/auth/login
{
  "email": "user@example.com",
  "password": "yourpassword"
}
```
**Login Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": { "id": "...", "email": "...", "name": "..." }
}
```

All subsequent requests require:
```
Authorization: Bearer <access_token>
```

---

### Chat

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat/message` | Send a chat message |
| GET | `/api/chat/history` | Get chat history |
| DELETE | `/api/chat/history` | Clear chat history |
| POST | `/api/chat/upload-context` | Upload context for chat |

**Send Message:**
```json
POST /api/chat/message
{
  "message": "Find me Python developer jobs in London",
  "session_id": "optional-uuid"
}
```

**Response:**
```json
{
  "response": "I found 5 jobs matching your profile...",
  "session_id": "uuid",
  "metadata": {
    "agent": "job_hunter",
    "action": "__TAILOR_APPLY__",
    "jobs": [...]
  }
}
```

---

### CV Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/cv/upload` | Upload CV file (PDF/DOCX) |
| GET | `/api/cv/list` | List all user CVs |
| GET | `/api/cv/{cv_id}` | Get specific CV + parsed data |
| DELETE | `/api/cv/{cv_id}` | Delete CV |
| POST | `/api/cv/{cv_id}/set-primary` | Set as primary CV |
| GET | `/api/cv/{cv_id}/tailored` | List tailored versions |

**Upload CV:**
```
POST /api/cv/upload
Content-Type: multipart/form-data
Body: file=<cv.pdf>
```

**Response:**
```json
{
  "cv_id": "uuid",
  "file_name": "my_cv.pdf",
  "parsed": true,
  "parsed_data": {
    "personal_info": { "name": "John Doe", "email": "..." },
    "skills": { "languages": ["Python", "TypeScript"], ... },
    "experience": [...],
    "education": [...]
  }
}
```

---

### Jobs

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/jobs/search` | Trigger a job search |
| GET | `/api/jobs/searches` | List past searches |
| GET | `/api/jobs/searches/{search_id}/jobs` | Jobs from a search |
| GET | `/api/jobs/{job_id}` | Get job detail |
| POST | `/api/jobs/{job_id}/tailor` | Tailor CV for job |
| GET | `/api/jobs/{job_id}/tailored-cv` | Get tailored CV |

**Search Jobs:**
```json
POST /api/jobs/search
{
  "query": "Senior Python Developer London",
  "target_role": "Python Developer",
  "target_location": "London, UK",
  "limit": 10
}
```

---

### Applications

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/applications` | List all applications |
| GET | `/api/applications/{id}` | Get application detail |
| POST | `/api/applications/{id}/approve` | Approve (HITL) |
| POST | `/api/applications/{id}/send` | Send email |
| PATCH | `/api/applications/{id}/status` | Update status |
| DELETE | `/api/applications/{id}` | Delete application |

---

### Dashboard

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/dashboard/stats` | Application stats |
| GET | `/api/dashboard/recent` | Recent activity |
| GET | `/api/dashboard/pipeline` | Active pipeline status |

**Dashboard Stats Response:**
```json
{
  "total_applications": 24,
  "sent": 18,
  "pending_approval": 3,
  "replied": 5,
  "interview_rate": "27.7%",
  "top_companies": ["Google", "Stripe", "Vercel"]
}
```

---

### Interview Prep

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/interview/prep` | Start interview prep for job |
| GET | `/api/interview/list` | List all prep sessions |
| GET | `/api/interview/{id}` | Get prep detail |
| GET | `/api/interview/{id}/download` | Download PPTX slides |

---

### Integrations

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/integrations/status` | Check connected services |
| GET | `/api/integrations/google/auth-url` | Get Google OAuth URL |
| POST | `/api/integrations/google/callback` | Handle OAuth callback |
| DELETE | `/api/integrations/google` | Disconnect Google |

---

### Observability

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/observability/executions` | Agent execution logs |
| GET | `/api/observability/quota` | API quota usage |
| GET | `/api/observability/errors` | Error log |

---

### Settings

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/settings` | Get user preferences |
| PATCH | `/api/settings` | Update preferences |

---

### System

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/` | Root info |
| GET | `/docs` | Swagger UI |
| GET | `/redoc` | ReDoc UI |
| WS | `/ws` | WebSocket endpoint |

---

## Frontend Architecture

### Component Hierarchy

```
App
└── Router
    ├── AuthPage (login/register)
    └── MainLayout
        ├── TopBar              ← User info, notifications, settings
        ├── LeftSidebar         ← Navigation tabs + data source panel
        │   ├── NavLink         ← Tab items (Chat, Jobs, Applications, etc.)
        │   └── FileUploadModal ← CV drag-drop upload
        ├── CenterPanel         ← Main content area
        │   ├── WelcomeScreen   ← First-time user onboarding
        │   ├── Chat View       ← Message bubbles + input
        │   │   ├── UserBubble  ← User messages (copy, edit)
        │   │   ├── AgentBubble ← AI responses (copy, thumbs, regenerate)
        │   │   └── chat-cards/ ← Rich action cards
        │   │       ├── TailorCard
        │   │       ├── CVApprovalCard
        │   │       ├── EmailApprovalCard
        │   │       ├── RegenerateCard
        │   │       └── InterviewCard
        │   ├── JobsView        ← Job search results + inline chat
        │   ├── ApplicationTracker ← Pipeline kanban
        │   ├── InterviewPrepView  ← Q&A display
        │   ├── SeeingInView    ← CV data viewer
        │   └── ObservabilityView  ← Logs + quota charts
        └── RightSidebar        ← Agent activity + draft previews
            ├── HitLBlock       ← HITL approval controls
            └── NotificationPanel ← Real-time alerts
```

### Zustand Store (`agent-store.ts`)

The global state store tracks:

```typescript
interface AgentStore {
  // Auth
  user: User | null
  token: string | null

  // Chat
  messages: Message[]
  sessionId: string | null
  isTyping: boolean

  // CV
  cvs: CV[]
  primaryCV: CV | null
  parsedCV: ParsedCV | null

  // Jobs
  jobSearches: JobSearch[]
  currentJobs: Job[]

  // Applications
  applications: Application[]

  // Agent status
  agentStatus: Record<string, AgentStatus>
  agentLogs: LogEntry[]

  // UI state
  activeView: ViewType
  drafts: {
    cv: TailoredCV | null
    email: EmailDraft | null
    coverLetter: string | null
  }
  notifications: Notification[]
}
```

### API Client (`api.ts`)

A typed fetch wrapper that:
- Automatically injects `Authorization: Bearer <token>` header
- Handles JSON serialisation/deserialisation
- Throws typed `ApiError` on non-2xx responses
- Supports file uploads via `FormData`

```typescript
// Example usage
const response = await api.post<ChatResponse>('/chat/message', {
  message: 'Find Python jobs in London',
  session_id: sessionId
})
```

### Chat Card System

When the AI response metadata includes an action, the `CenterPanel` renders a rich card instead of (or alongside) a text bubble:

| Action Prefix | Card Component | Purpose |
|--------------|---------------|---------|
| `__TAILOR_APPLY__` | `TailorCard` | "Tailor CV for this job" button |
| `__APPROVE_CV__` | `CVApprovalCard` | Shows tailored CV diff + approve button |
| `__SEND_EMAIL__` | `EmailApprovalCard` | Shows email preview + send button |
| `__REGENERATE_CV__` | `RegenerateCard` | One-click CV regeneration |
| `__PREP_INTERVIEW__` | `InterviewCard` | Triggers interview prep |

Action cards call `sendAction(action)` which sends the action prefix silently (no user message bubble shown).

### Jobs View Chat

The `JobsView` component injects a `[JOBS_VIEW]` context block before every user message:

```
[JOBS_VIEW]
You are helping the user explore these specific job listings:
Job 1: Senior Python Developer at Google — London, UK — Match: 87%
Job 2: Backend Engineer at Stripe — Remote — Match: 82%
...
Only answer questions about these jobs.
[/JOBS_VIEW]
```

This ensures the AI only discusses the currently displayed jobs.

---

## WebSocket Protocol

**Endpoint:** `wss://localhost:8000/ws`

### Authentication

On connection, the client sends an auth message as the first WebSocket frame:

```json
{
  "type": "auth",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

The server responds:
```json
{ "type": "auth_ok", "user_id": "uuid" }
```

### Server → Client Events

| Event Type | Payload | When |
|------------|---------|------|
| `auth_ok` | `{ user_id }` | Auth success |
| `auth_error` | `{ message }` | Auth failed |
| `agent_started` | `{ agent, session_id }` | Agent begins work |
| `agent_progress` | `{ agent, message, progress }` | Incremental update |
| `agent_completed` | `{ agent, result }` | Agent finished |
| `agent_error` | `{ agent, error }` | Agent failed |
| `workflow_update` | `{ step, status }` | Pipeline stage change |
| `approval_requested` | `{ type, data }` | HITL pause |
| `log_entry` | `{ level, message, agent }` | Debug log |
| `notification` | `{ title, body, type }` | System notification |
| `gmail_reply` | `{ from, subject, preview }` | Recruiter replied |

### Client → Server Events

| Event Type | Payload | Purpose |
|------------|---------|---------|
| `auth` | `{ token }` | Authenticate |
| `ping` | `{}` | Keep-alive |

---

## LLM Router & Fallback Chain

**File:** `backend/app/core/llm_router.py`

The system never throws if one LLM is unavailable. It tries models in order:

```
gpt-oss-120b (Groq)          → Primary
  │ fail / rate-limit
  ▼
gemini-2.5-flash (Google)    → Secondary
  │ fail / rate-limit
  ▼
llama-3.3-70b (Groq)         → Fallback 1
  │ fail
  ▼
mixtral-8x7b (Groq)          → Fallback 2
  │ fail
  ▼
llama-3.1-8b (Groq)          → Last resort
```

LangChain's `with_fallbacks()` is used for automatic runtime error recovery (including 429 rate limit errors).

### Model Configurations

| Model | Provider | RPM | RPD | TPM |
|-------|----------|-----|-----|-----|
| gpt-oss-120b | Groq | 15 | 1,500 | 1,000,000 |
| gemini-2.5-flash | Google | 15 | 1,500 | 1,000,000 |
| llama-3.3-70b | Groq | 30 | 14,400 | 131,072 |
| mixtral-8x7b | Groq | 30 | 14,400 | 131,072 |
| llama-3.1-8b | Groq | 30 | 14,400 | 131,072 |

### Usage

```python
from app.core.llm_router import get_llm

# Get best available LLM (task label for observability)
llm = get_llm(task="cv_tailor")
response = await llm.ainvoke(prompt)

# Request a specific model with fallbacks
llm = get_llm(preferred_model="gemini-2.5-flash", temperature=0.7)
```

---

## Skills System

**Directory:** `skills/`

The skills system provides structured prompting guidance loaded from Markdown files. Each skill file contains expert-level instructions that are injected into agent prompts.

### Available Skills

| File | Purpose |
|------|---------|
| `01-email-writing/` | AIDA email composition guidelines |
| `02-cover-letter-writting/` | Cover letter structure and tone |
| `03-cv-resume-writing/` | CV formatting and content best practices |
| `04-regional-adaptation/` | Adapting applications for different countries (UK, US, EU, MENA, APAC) |
| `05-ats-optimization/` | ATS keyword injection strategies |
| `_shared/` | Shared guidelines (professional tone, formatting) |

### How Skills Are Used

```python
from app.core.skills import load_skill

# Load skill content for injection into prompt
email_skill = load_skill("01-email-writing")
prompt = f"""
{email_skill}

Now compose an email for:
Job: {job['title']} at {job['company']}
Candidate: {cv_data['personal_info']['name']}
"""
```

---

## Human-in-the-Loop (HITL)

Digital FTE is designed around a **human-first** philosophy. The system never sends emails without explicit user approval.

### HITL Flow

```
1. Agent completes CV + Email draft
2. LangGraph pauses at human_approval node
3. WebSocket emits: approval_requested event
4. Frontend renders EmailApprovalCard in chat
5. User can:
   a. Click "Approve & Send" → action prefix sent → pdf_generator → email_sender
   b. Type feedback → editor_node rewrites → back to human_approval
   c. Click "Regenerate" → cv_tailor reruns with new prompt
6. After approval:
   - PDF generated
   - Email sent via Gmail API
   - Application status updated to "sent"
```

### HITL State Fields

```python
# In DigitalFTEState:
waiting_for_user: bool       # True while paused at approval node
user_approvals: dict         # { job_id: { "approved": True } }
draft_cv: Optional[dict]     # CV awaiting approval
draft_email: Optional[dict]  # Email awaiting approval
draft_cover_letter: str      # Cover letter awaiting approval
```

### Editor Node

When the user provides feedback instead of approval, the `editor_node`:
1. Receives the user's feedback as `user_message`
2. Sends current drafts + feedback to LLM
3. Gets back updated email/cover letter JSON
4. Clears the job's approval status
5. Routes back to `supervisor` → `human_approval` (re-shows for review)

---

## Observability & Monitoring

### LangSmith

Set in `.env`:
```
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls__...
LANGCHAIN_PROJECT=digital-fte
```

All LangChain/LangGraph invocations are automatically traced.

### Langfuse

Set in `.env`:
```
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com
```

Provides prompt-level analytics, cost tracking, and performance dashboards.

### Agent Execution Logs

Every agent action is logged to the `agent_executions` table with:
- Input/output state snapshots
- LLM model used + token counts
- Execution time in milliseconds
- Trace IDs for LangSmith/Langfuse correlation

### API Quota Dashboard

The `ObservabilityView` frontend component displays:
- Per-provider daily request and token usage
- Visual progress bars against limits
- Historical usage charts (recharts)
- Collapsible API usage section (defaults to collapsed)

---

## Configuration Reference

All configuration is in `.env` (copy from `.env.example`).

### Required Variables

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | JWT signing secret (min 32 chars) |
| `GOOGLE_AI_API_KEY` | Google Gemini API key |

### LLM Providers

| Variable | Description | Get it |
|----------|-------------|--------|
| `GOOGLE_AI_API_KEY` | Gemini API key | [ai.google.dev](https://ai.google.dev) |
| `GROQ_API_KEY` | Groq API key | [console.groq.com](https://console.groq.com) |

### Job Search

| Variable | Description | Get it |
|----------|-------------|--------|
| `SERPAPI_API_KEY` | Google Jobs search | [serpapi.com](https://serpapi.com) |
| `RAPIDAPI_KEY` | Job board aggregator | [rapidapi.com](https://rapidapi.com) |

### HR Contact Finding

| Variable | Description | Free Tier |
|----------|-------------|-----------|
| `HUNTER_API_KEY` | Hunter.io email finder | 25/month |
| `PROSPEO_API_KEY` | Prospeo email finder | 150/month |
| `APIFY_API_KEY` | LinkedIn scraper | Limited |
| `SNOV_CLIENT_ID` | Snov.io client ID | 50/month |
| `SNOV_CLIENT_SECRET` | Snov.io client secret | 50/month |

### Google Cloud (Gmail)

| Variable | Description |
|----------|-------------|
| `GOOGLE_CLOUD_PROJECT_ID` | GCP project ID |
| `GOOGLE_OAUTH_CLIENT_ID` | OAuth 2.0 client ID |
| `GOOGLE_OAUTH_CLIENT_SECRET` | OAuth 2.0 client secret |
| `GOOGLE_CREDENTIALS_PATH` | Path to credentials.json |

### Database

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | SQLAlchemy DB URL (defaults to SQLite) |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_ANON_KEY` | Supabase anon key |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key |
| `DIRECT_DATABASE_URL` | Direct Postgres URL (for migrations) |

### Cache

| Variable | Description |
|----------|-------------|
| `UPSTASH_REDIS_URL` | Redis connection URL |
| `UPSTASH_REDIS_REST_URL` | REST API URL |
| `UPSTASH_REDIS_REST_TOKEN` | REST API token |

### Observability

| Variable | Description |
|----------|-------------|
| `LANGCHAIN_TRACING_V2` | Enable LangSmith tracing |
| `LANGCHAIN_API_KEY` | LangSmith API key |
| `LANGCHAIN_PROJECT` | LangSmith project name |
| `LANGFUSE_PUBLIC_KEY` | Langfuse public key |
| `LANGFUSE_SECRET_KEY` | Langfuse secret key |
| `LANGFUSE_HOST` | Langfuse host URL |

### App Config

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_ENV` | `development` | Environment name |
| `DEBUG` | `true` | Debug mode |
| `LOG_LEVEL` | `DEBUG` | Log verbosity |
| `UPLOAD_DIR` | `./uploads` | CV upload directory |
| `GENERATED_DIR` | `./generated` | PDF/PPTX output directory |

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+ (or Bun)
- Git

### 1. Clone the Repository

```bash
git clone https://github.com/Azan345345/HR-FTE.git
cd HR-FTE
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env and fill in your API keys
```

At minimum, set:
```env
SECRET_KEY=your-super-secret-key-at-least-32-chars
GOOGLE_AI_API_KEY=your-gemini-api-key
```

### 4. Start the Backend

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API:** http://localhost:8000
- **Swagger docs:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **Health:** http://localhost:8000/health

### 5. Frontend Setup

```bash
cd frontend

# Install dependencies (npm, yarn, or bun)
npm install
# or
bun install
```

### 6. Start the Frontend

```bash
npm run dev
# or
bun run dev
```

The frontend will be available at http://localhost:5173

### 7. Create Your First Account

1. Open http://localhost:5173
2. Click "Register"
3. Enter your name, email, and password
4. Upload your CV (PDF or DOCX) from the Left Sidebar → Data Sources
5. Start chatting: "Find me Python developer jobs in London"

---

## Environment Setup

### Development (SQLite)

No database configuration needed. SQLite database (`digital_fte.db`) is auto-created in the `backend/` directory on first run.

### Production (Supabase PostgreSQL)

1. Create a [Supabase](https://supabase.com) project
2. Copy the connection strings from Supabase dashboard
3. Set in `.env`:
   ```env
   DATABASE_URL=postgresql+asyncpg://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres
   DIRECT_DATABASE_URL=postgresql://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres
   ```
4. Tables are auto-created on startup via `Base.metadata.create_all`

### Gmail Integration Setup

1. Create a Google Cloud project at [console.cloud.google.com](https://console.cloud.google.com)
2. Enable the **Gmail API**
3. Create OAuth 2.0 credentials (Desktop or Web application)
4. Download `credentials.json` to the backend directory
5. Set in `.env`:
   ```env
   GOOGLE_CLOUD_PROJECT_ID=your-project-id
   GOOGLE_OAUTH_CLIENT_ID=your-client-id
   GOOGLE_OAUTH_CLIENT_SECRET=your-client-secret
   GOOGLE_CREDENTIALS_PATH=./credentials.json
   ```
6. In the app: Settings → Integrations → Connect Google → Complete OAuth flow

### Redis Setup (Optional)

For caching and rate limiting, create a free [Upstash Redis](https://upstash.com) database:

```env
UPSTASH_REDIS_URL=rediss://default:<password>@<endpoint>.upstash.io:6379
UPSTASH_REDIS_REST_URL=https://<endpoint>.upstash.io
UPSTASH_REDIS_REST_TOKEN=AXxxxxxxxxxxxxxxxx
```

---

## Running in Production

### Backend (Uvicorn + Gunicorn)

```bash
cd backend
pip install gunicorn

gunicorn app.main:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers 4 \
  --bind 0.0.0.0:8000 \
  --timeout 120
```

### Frontend (Static Build)

```bash
cd frontend
npm run build
# Serve the dist/ folder with Nginx or any static host
```

### Environment Variables for Production

```env
APP_ENV=production
DEBUG=false
LOG_LEVEL=INFO
SECRET_KEY=<very-long-random-string>
DATABASE_URL=postgresql+asyncpg://...  # Supabase
```

### Nginx Configuration (Example)

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    # Frontend
    location / {
        root /var/www/digital-fte/dist;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # WebSocket
    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

---

## Known Limitations & Roadmap

### Current Known Gaps

- **Rate limiting** — Tracked in `api_quota_usage` table but not enforced at API gateway level
- **Gmail OAuth** — Untested end-to-end in production; requires real Google Cloud credentials
- **pgvector** — Full vector search requires Supabase; SQLite uses basic text matching as fallback
- **LangSmith/Langfuse** — Needs env vars configured to activate tracing
- **Follow-up emails** — Automated follow-up logic is stubbed but not fully implemented
- **Multi-CV management** — Only the primary CV is used in the pipeline

### Planned Features

- [ ] LinkedIn Easy Apply automation
- [ ] Indeed / Glassdoor direct application support
- [ ] Automated follow-up email sequences (3-day, 7-day, 14-day)
- [ ] Recruiter reply sentiment analysis
- [ ] Cover letter A/B testing
- [ ] Application analytics dashboard with conversion funnel
- [ ] Multi-language CV support (Arabic, French, German)
- [ ] Browser extension for job scraping
- [ ] Mobile app (React Native)
- [ ] Team/agency mode (multiple candidates)

---

## Contributing

Contributions are welcome! Please follow these steps:

### Setup for Development

```bash
# Fork and clone
git clone https://github.com/YOUR_USERNAME/HR-FTE.git
cd HR-FTE

# Create a feature branch
git checkout -b feature/your-feature-name

# Set up backend
cd backend && python -m venv venv && venv/Scripts/activate  # Windows
pip install -r requirements.txt

# Set up frontend
cd ../frontend && npm install
```

### Code Style

- **Python:** Follow PEP 8. Use `structlog` for all logging (no `print()`).
- **TypeScript:** Strict mode enabled. No `any` types.
- **Commits:** Conventional commits format (`feat:`, `fix:`, `docs:`, `refactor:`)

### Adding a New Agent

1. Create `backend/app/agents/your_agent.py`
2. Add an async function as the entry point
3. Add a node in `backend/app/agents/graph.py`:
   ```python
   async def your_agent_node(state: DigitalFTEState) -> dict:
       from app.agents.your_agent import your_function
       result = await your_function(state.get("some_field"))
       return {"new_field": result, "current_agent": "your_agent"}

   workflow.add_node("your_agent", your_agent_node)
   workflow.add_edge("your_agent", "supervisor")
   ```
4. Add routing in `route_from_supervisor`:
   ```python
   "your_step": "your_agent",
   ```
5. Update supervisor to route to it when appropriate

### Running Tests

```bash
cd backend
pytest tests/ -v

cd frontend
npm run test
```

### Pull Request Guidelines

- Keep PRs focused on a single feature or fix
- Update the README if you add new configuration or features
- All new agents must have at least one test in `backend/tests/`
- Frontend components must be typed (no implicit `any`)

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Acknowledgements

Built with:
- [LangChain](https://langchain.com) & [LangGraph](https://langchain-ai.github.io/langgraph/) — Agent orchestration
- [Google Gemini](https://deepmind.google/technologies/gemini/) — Primary LLM
- [Groq](https://groq.com) — Ultra-fast LLM inference
- [FastAPI](https://fastapi.tiangolo.com) — Backend framework
- [Supabase](https://supabase.com) — Database & auth
- [shadcn/ui](https://ui.shadcn.com) — UI components
- [ReportLab](https://www.reportlab.com) — PDF generation
- [Hunter.io](https://hunter.io) — HR email finding

---

<div align="center">
Made with purpose — to put the human back in the loop while letting AI do the heavy lifting.

**[⭐ Star this repo](https://github.com/Azan345345/HR-FTE)** if Digital FTE helped you land a job!
</div>
