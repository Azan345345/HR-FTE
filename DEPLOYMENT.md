# Digital FTE Deployment Guide

Complete instructions for setting up and deploying the Digital FTE Multi-Agent AI System.

## Prerequisites
- Docker & Docker Compose
- API Keys:
  - Google Gemini / Groq (for LLM)
  - SerpAPI / JSearch (for job scraping)
  - Hunter.io / Apollo.io (for HR search)
  - Gmail API (OAuth credentials)

## Quick Start (Docker)

1. **Clone the repository**
2. **Configure Environment Variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```
3. **Launch the stack**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d --build
   ```
4. **Run Migrations**
   ```bash
   docker-compose exec backend alembic upgrade head
   ```

## Development Setup

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Security & Reliability
- **Rate Limiting**: Enforced via `slowapi` on all public endpoints.
- **Auth**: Protected by JWT (RS256).
- **Quotas**: LLM and API usage tracked per-user in Redis.
- **Fallbacks**: Multiple LLM models configured for automatic failover.

## Support
For issues or feature requests, please consult the `walkthrough.md` or system logs via the Observability dashboard.
