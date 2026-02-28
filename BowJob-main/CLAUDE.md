# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

BowJob is a microservices platform for AI-powered CV/resume processing with two FastAPI services:
- **CV Parser** (port 8000) - Extracts structured JSON from PDF resumes using OpenAI GPT-4o-mini
- **CV-JD Matching** (port 8001) - Analyzes CVs against job descriptions with scoring and improvement suggestions

## Development Commands

```bash
# Run all services via Docker
docker-compose up -d --build

# Run individual services (development with auto-reload)
cd bowjob-cv-parser && python app_v3.py   # Port 8000
cd cv-jd-matching && python app.py         # Port 8001

# Test endpoints
curl http://localhost:8000/health
curl http://localhost:8001/health
curl -X POST http://localhost:8000/parse -F "file=@cv.pdf"

# Run scoring tests (cv-jd-matching)
cd cv-jd-matching && python test_scoring.py
```

## Architecture

### Data Flow
```
PDF Upload → CV Parser (GPT-4o-mini extraction) → Parsed JSON → CV-JD Matching → Analysis + Improvements
```

### CV Parser (`bowjob-cv-parser/`)
- `app_v3.py` - FastAPI app with `/parse` endpoint (PDF multipart upload)
- `parser_v3.py` - `CVParserV3` class using OpenAI function calling with structured schema
  - Uses PyPDF2 for text extraction
  - Returns NULL for missing data (no placeholders)
  - Calculates `total_years_of_experience` excluding gaps

### CV-JD Matching (`cv-jd-matching/`)
- `app.py` - FastAPI app with session-based stateful endpoints
- `improvement_engine.py` - `CVImprovementEngine` class containing:
  - **Deterministic scoring** (`calculate_match_score`) - 100-point scale with weighted components:
    - Skills: 35pts, Experience: 25pts, Education: 15pts, Projects: 15pts, Keywords: 10pts
  - **AI analysis** via OpenAI function calling with industry-specific terminology
  - **Project guardrail** - Ensures minimum 3 projects in output
  - **Section chat** - Context-aware chat with pending actions system

### Session Management (In-Memory)
The matching service uses in-memory session storage (dict) for:
- Tracking `current_cv` state with approved changes
- `pending_actions` / `confirmed_actions` for chat-based modifications
- Chat history for context retention

## Key Implementation Details

### Scoring System
Scores are deterministic (same input = same output) calculated in `calculate_match_score()`:
- Extracts keywords from JD using regex patterns
- Matches against CV text (skills, work experience, projects)
- Rating: Poor (<50), Fair (50-64), Good (65-79), Excellent (80+)

### CV Sections Distinction
In improvement_engine.py analysis:
- `cv_sections` - Modifications to EXISTING content (tag: "modified")
- `non_cv_sections` - NEW content for NULL/empty sections (tag: "new")

### Action System
Chat endpoint returns optional `action` objects with `status: "pending"`. Users approve via `/api/v1/approve` which:
1. Applies changes to `current_cv` in session
2. Recalculates match score
3. Returns updated CV state

## Environment Variables
```
OPENAI_API_KEY=required
PORT=8000|8001 (default per service)
ENV=development|production (enables auto-reload)
```

## API Docs
- http://localhost:8000/docs (CV Parser)
- http://localhost:8001/docs (CV-JD Matching)
