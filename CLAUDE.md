# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Digital FTE / CareerAgent** — AI-powered multi-agent system that automates job applications end-to-end: CV parsing → job search → CV tailoring → HR contact finding → email composition → human approval → Gmail sending → interview prep.

## Development Commands

### Backend (FastAPI + Python 3.12)
```bash
cd backend

# Install dependencies (use venv)
python -m venv venv && source venv/Scripts/activate  # Windows Git Bash
pip install -r requirements.txt

# Run dev server (port 8080)
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

# Syntax check (no test suite exists)
python -c "import py_compile; py_compile.compile('app/agents/supervisor.py', doraise=True)"
```

### Frontend (React 18 + Vite + TypeScript)
```bash
cd frontend
npm install
npm run dev          # Dev server on :5173, proxies /api → localhost:8080
npm run build        # Production build
npx tsc --noEmit     # Type check
npm run lint         # ESLint
npm run test         # Vitest
```

### Environment
Copy `.env.example` → `.env` at project root. Minimum required: one LLM key (`GOOGLE_AI_API_KEY` or `GROQ_API_KEY`) and one job search key (`SERPAPI_API_KEY` or `RAPIDAPI_KEY`).

## Architecture

### Request Flow (Production)
```
Browser → Vercel (frontend/vercel.json rewrites /api/* → Railway) → FastAPI backend
Browser → WebSocket /ws → FastAPI WebSocket handler (JWT auth on first message)
```

Vercel has a ~120s proxy timeout. Backend operations that exceed this cause 502 errors visible to users, even though processing continues and WebSocket events still arrive.

### Backend Structure (`backend/app/`)

**Entry point:** `main.py` — FastAPI app with lifespan (creates tables, runs migrations, starts Gmail watcher). Routes mounted at `/api` via `api/router.py`.

**Two parallel agent systems exist:**
1. **Supervisor (primary, used by chat):** `agents/supervisor.py` — a 3000+ line monolith that handles ALL chat messages. Routes via keyword classification (`_keyword_classify`) or LLM intent detection. Returns `Tuple[str, Optional[dict]]` where the dict drives rich UI cards. Action prefix routing (`__TAILOR_APPLY__:`, `__SEND_EMAIL__:`, etc.) handles button clicks from chat cards.
2. **LangGraph (legacy):** `agents/graph.py` + `agents/state.py` — StateGraph with `DigitalFTEState`. Still used by `orchestration/pipeline_controller.py` but most chat flows bypass it and call agents directly from supervisor.

**Key agents (all in `agents/`):**
- `supervisor.py` — Intent router + orchestrator. Contains `_handle_job_search_v2`, `_handle_auto_pipeline`, `_handle_tailor_apply`, `_handle_send_email`, `_bg_hr_lookup`, and the multi-agent planner `_orchestrate_agents`.
- `job_hunter.py` — Multi-source job search (Apify Indeed/LinkedIn, SerpAPI, JSearch) with cross-platform deduplication and CV-based scoring.
- `cv_tailor.py` — LLM-powered CV tailoring with skills injection from `skills/` markdown files.
- `hr_finder.py` — Multi-provider HR contact discovery (Hunter.io, Prospeo, Snov, Apollo, website scraping).
- `email_sender.py` — Email composition (AIDA framework) + Gmail API sending with PDF attachment.
- `cv_parser.py` — PDF/DOCX parsing to structured JSON.
- `doc_generator.py` — ReportLab PDF generation for tailored CVs.

**Core infrastructure (`core/`):**
- `llm_router.py` — LLM selection with automatic fallback chain: OpenAI → Gemini 2.5 Flash → Groq Llama 3.3 → Mixtral → Llama 3.1 8B. `get_llm(task=)` returns a LangChain `BaseChatModel`.
- `event_bus.py` — WebSocket pub/sub. `event_bus.emit(user_id, event_type, data)` broadcasts to all user connections. Event types: `agent_started`, `agent_progress`, `agent_completed`, `agent_error`, `workflow_update`, `jobs_stream`, `hr_stream`.
- `security.py` — JWT (HS256, 24h) + bcrypt password hashing.
- `skills.py` — Loads markdown skill files from `skills/` directory, injected into CV tailor prompts.

**Database (`db/`):**
- `database.py` — Async SQLAlchemy with `AsyncSessionLocal`. SQLite for dev, Supabase PostgreSQL for prod. `get_db()` is the FastAPI dependency.
- `models.py` — 14 ORM models. Key relationships: User → UserCV → Job (via JobSearch) → TailoredCV → HRContact → Application.

### Frontend Structure (`frontend/src/`)

**Single-page app** with three-panel layout: `LeftSidebar.tsx` (nav + conversations) | `CenterPanel.tsx` (chat + cards) | `RightSidebar.tsx` (agent activity).

**State management (Zustand stores in `stores/`):**
- `agent-store.ts` — Agent statuses, log entries, job stream state, HR statuses. Updated by WebSocket events from `hooks/useWebSocket.ts`.
- `auth-store.ts` — JWT token + user info, persisted to localStorage.

**API layer:**
- `lib/api.ts` — Typed fetch wrapper with JWT injection, 401 auto-redirect, abort support. Uses relative URLs (Vite proxy in dev, Vercel rewrites in prod).
- `services/api.ts` — Domain-specific functions (uploadCV, sendChatMessage, etc.) built on `api()`.

**Chat cards (`components/chat-cards/`):** Rich interactive cards rendered from supervisor metadata: `JobResultsCard`, `CVReviewCard`, `EmailReviewCard`, `ApplicationSentCard`, `InterviewPrepCard`, `CVSelectionCard`, `CVImprovementActionCard`, `CVImprovedCard`. Each card uses `sendAction()` to dispatch `__ACTION_PREFIX__:id` messages back to the supervisor.

### Critical Patterns

**Supervisor returns metadata for UI cards:** Every handler returns `(text, metadata_dict_or_None)`. The `type` field in metadata (`job_results`, `cv_review`, `email_review`, `application_sent`, `interview_prep`, `cv_selection`, `cv_improved`) determines which chat card component renders.

**Background HR lookup:** Job search returns results immediately, then fires `_bg_hr_lookup` as an asyncio background task. HR results stream to frontend via `hr_stream` WebSocket events. The tailor flow checks for pre-fetched HR contacts in DB before doing a live lookup.

**LLM calls are the latency bottleneck:** Each LLM call takes 5-10s. Multiple serial LLM calls in a request path can push total time past the 120s Vercel proxy timeout. Minimize serial LLM calls in any HTTP request handler.

## Deployment

- **Backend:** Railway (auto-deploys from `main` push). Dockerfile in `backend/`. Port 8080.
- **Frontend:** Vercel (auto-deploys). Config in `frontend/vercel.json`. Rewrites `/api/*` to Railway backend URL.
- **Database:** Supabase PostgreSQL (prod), SQLite file `backend/digital_fte.db` (dev).

## Conventions

- Backend uses `structlog` for logging, not `print()`.
- All DB operations use async SQLAlchemy (`await db.execute(select(...))`).
- Frontend uses `@/` path alias (maps to `frontend/src/`).
- UI components from shadcn/ui in `frontend/src/components/ui/` — don't modify these directly.
- The `skills/` directory contains markdown prompt templates injected into CV tailor LLM calls via `core/skills.py`.
- No test suite exists for the backend. Verify changes with `py_compile` and manual testing.
