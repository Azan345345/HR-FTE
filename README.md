# Digital FTE — AI-Powered Job Application Assistant

An AI multi-agent system that acts as a full-time employee dedicated to your job search. It parses your CV, finds matching jobs, tailors your CV per job at 100% match, finds HR contacts, sends applications, and prepares you for interviews.

## Architecture

- **Backend**: FastAPI + Python 3.12
- **Frontend**: Next.js 14 + shadcn/ui + Tailwind CSS
- **AI Orchestration**: LangGraph + LangChain
- **LLMs**: Gemini 2.0 Flash (primary) + Groq Llama/Mixtral (fallback) — all free tier
- **Database**: PostgreSQL 16 + Redis 7 + ChromaDB
- **Observability**: LangSmith + LangFuse

## Agents

| Agent | Role |
|-------|------|
| Supervisor | Routes tasks to specialized agents |
| CV Parser | Extracts structured data from CV |
| Job Hunter | Searches jobs across LinkedIn, Indeed, Glassdoor |
| CV Tailor | Rewrites CV to match each job at 100% |
| HR Finder | Finds hiring manager contact info |
| Email Sender | Sends applications via Gmail API |
| Interview Prep | Generates interview preparation materials |
| Doc Generator | Creates PDFs and PPTX files |

## Quick Start

```bash
# 1. Clone and copy env
cp .env.example .env
# Edit .env with your API keys

# 2. Start infrastructure
docker compose up -d postgres redis chromadb

# 3. Backend
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8080

# 4. Frontend
cd frontend
npm install
npm run dev
```

## Project Structure

```
digital-fte/
├── backend/          # FastAPI + Agents
│   ├── app/
│   │   ├── agents/   # LangGraph agents
│   │   ├── api/      # REST + WebSocket
│   │   ├── core/     # LLM router, auth, events
│   │   ├── db/       # Database, Redis, ChromaDB
│   │   ├── schemas/  # Pydantic models
│   │   ├── services/ # Business logic
│   │   └── templates/# CV/email templates
│   └── migrations/
├── frontend/         # Next.js 14
│   └── src/
│       ├── app/      # Pages (App Router)
│       ├── components/
│       ├── hooks/
│       ├── lib/
│       ├── stores/
│       └── types/
└── docker-compose.yml
```

See [DIGITAL_FTE_PLAN.md](./DIGITAL_FTE_PLAN.md) for the complete specification.
